# Static Baseline Result

The static agent received only PRESTATE, the Formation Oracle, the registered
comparison plan and baseline repository code. It was forbidden to read
formation rounds, open reviews or current uncommitted implementations, to
probe, to ask questions, or to edit.

## Outcome

The static agent correctly judged the pre-state unable to reach the oracle and
proposed a plausible one-shot architecture:

- producer/consumer authority separation;
- persistent consumer state and canonical readback;
- coarse opaque revisioned receipt;
- authorization, integrity, replay/correction/revocation and privacy checks;
- a commandless external World ingress and Source Map;
- producer-only, wrong-authority, stale and refusal controls.

It predicted medium-confidence oracle reachability if fully implemented.

## Important differences from the formed result

The baseline did not produce a runnable state change or target adoption. It
also prescribed mechanisms not grounded in the available local authority:
signing keys, key IDs, signatures and fixed validity. The model-principal
episode initially made a similar move, but reciprocal refusal plus local
probes removed those fields because no real key issuer or rotation authority
existed.

The static proposal also suggested a new projection plus removal for each
revision. Actual C4 duplicate-ID and stale-success analysis selected one stable
projection with reference-only update deltas.

## Fair verdict

Static reasoning was strong enough to discover much of the conceptual design,
so the experiment does **not** support “only A2A can invent the method”.
Adaptive A2A's observed increment was local falsification and countercondition
reduction: it converted a plausible design into a bounded runnable interface
through five defeated source implementations and an open World review.
