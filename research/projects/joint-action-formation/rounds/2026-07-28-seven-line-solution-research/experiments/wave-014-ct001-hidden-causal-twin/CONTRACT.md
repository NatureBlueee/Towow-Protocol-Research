# CT-001 Hidden Causal Twin Contract

## Question

When the same requested Target state is reached in two worlds, can the
evaluator distinguish:

1. the state being caused by A4's exact signed commit; and
2. A4's commit being suppressed while an independent Helper signs and causes
   an equivalent commit?

The experiment tests direct causal attribution at the Target atomic-commit
boundary. It does not claim global philosophical or but-for causation.

## Frozen worlds

Both worlds spawn the same four child-process roles with the
`multiprocessing.spawn` start method:

- `A4`
- `ROUTER`
- `HELPER`
- `TARGET`

Every child creates a distinct Ed25519 private key inside its own process.
Private keys are never returned to the controller.

The private intervention is:

- `W_G`: Router forwards A4's signed exact commit to Target.
- `W_F`: Router suppresses A4's commit and opens a pre-frozen window in which
  Helper independently signs the equivalent commit.

The private world mode is supplied only to Controller, Router and Helper.
Target receives an actor registry but no world mode. A4 receives only an
actor-neutral public manifest and Router endpoint.

## Pre-decision equivalence

The pre-decision prefix ends after A4 has:

1. started;
2. prepared its exact signed commit; and
3. sent that commit.

It ends before Router returns an observation. The two prefixes must have the
same alpha shape after scalar values are replaced by type and string-length
classes. No semantic world label may appear in A4's manifest, transcript,
argv, cwd or process name.

This is structural indistinguishability for the implemented A4-visible
surface. It is not a timing-side-channel proof.

## Target-native authority

Target verifies the request signature against its frozen actor registry and
atomically creates a signed receipt binding:

- direct actor identity and process identity;
- origin request ID, digest and signature;
- ingress channel;
- object and operation;
- pre-state and post-state;
- pre-version and post-version;
- Target commit ID.

Target's signed receipt is authoritative for direct actor attribution. A
Router record is corroborating route evidence and cannot override it.

Target additionally signs an authoritative readback binding the same
post-state and version to `last_commit_id`. The provenance-free state
projection remains byte-identical across the two worlds; causal provenance is
kept in the separate signed commit/readback layer rather than smuggled into
the compared state.

## Evaluators

`OUTCOME_ONLY_LEGACY` reads only Target state projection. It is expected to
report `SUCCEEDED` in both worlds.

`TARGET_NATIVE_CAUSAL` verifies process identities, request signatures, Target
receipt, authoritative readback, world bundle digest, causal bindings, ingress
channel and Router record. It must report:

| World | TargetStateSatisfied | ExactTaskSuccess | disposition |
|---|---:|---:|---|
| W_G | true | true | `SUCCEEDED` |
| W_F | true | false | `MATCHING_STATE_EXTERNAL_CAUSE` |

Missing or tampered provenance produces `INVALID_EVIDENCE`, never success.
Projection, readback and commit must agree; a rewritten projection or detached
readback is invalid evidence rather than an unsuccessful but valid world.

## Non-claims

- The synthetic state transition is not a real-world effect.
- Same alpha shape does not prove equality of scheduling or timing channels.
- A pre-frozen Helper plan reduces request-content dependence, but the window
  is opened after Router observes A4's request. The experiment establishes the
  direct committing actor, not full but-for independence from A4's activity.
- Process-private keys and signatures provide provenance within the trusted
  local-controller/process-isolation threat model. They do not resist a
  malicious process with arbitrary host-memory or directory access.
