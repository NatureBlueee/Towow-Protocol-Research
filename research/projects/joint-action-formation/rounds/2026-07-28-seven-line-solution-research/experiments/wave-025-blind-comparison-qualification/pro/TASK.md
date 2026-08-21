# External clean-room task — Wave 025

Task ID: `W025-BLIND-QUALIFICATION-CLEANROOM-001`  
Packet version: computed from this file before send

## Question

Design the smallest falsifiable qualification experiment that can establish—or reject—that a comparison of five heterogeneous decision treatments on hidden-world action tasks is not being driven by answer leakage, run-order contamination, evaluator feedback, controller substitution, or post-hoc applicability selection.

The treatments are intentionally heterogeneous: a lawful strong center, an equal-information center without substituted authority, a general model plus mature execution stack, a deterministic mature composition, and a real human institution. Fairness must not give a treatment information or authority it would not lawfully possess, and must not erase its native modality.

## Why it matters

Without a valid qualification experiment, any later winner or coverage claim may only measure experiment leakage or unequal problem definitions. A passing result should admit a later bounded comparison; a failing result should identify the exact disqualifying channel.

## Evidence you may use

- The task family freezes an exact problem, value floor, object, target, operation, authority topology, allowed actions, failure schedule, native effects and owner acceptance.
- One earlier experiment recorded identical payload, request, argv, environment, working directory and state path across hidden worlds, but still failed blindness because it always ran worlds in fixed order and all processes shared a same-user readable filesystem/process surface.
- Candidate treatments must be able to receive lawful task responses after interaction begins; hiding the experimental answer must not hide reality they would legitimately observe.
- Existing platforms, containers, VMs, statistical methods, human-study designs, adapters or combinations count as a successful answer. No novel protocol is required.

## Current known state

- Supported: recorded-field equality alone is insufficient.
- Failed: fixed execution order plus same-user shared runtime state does not establish blindness.
- Unknown: the minimum empirical and architectural evidence that is sufficient to admit a heterogeneous comparison without pretending to prove universal noninterference.

## Required result

Produce an experiment design, not a general essay. It must distinguish accidental leakage from a weak detector; separate applicability/authority fairness from information fairness; and identify what can honestly be concluded after a pass or failure.

## Success means

- A local implementer can build the qualification challenge without guessing its hidden oracle, positive control, randomization, isolation, or acceptance rule.
- The design includes at least one attack capable of detecting a deliberately inserted leak and at least one counterexample that would invalidate an apparently green batch.
- Claims are scoped to the tested observation and threat model.

## Hard boundaries

- Do not assume access to local files, tools, tests, or unlisted history.
- Do not report proposed or authorized action as executed.
- Do not invent measurements, citations or external acceptance.
- Do not rank the five treatments or assume any expected winner.
- Do not optimize for a proprietary or novel answer; mature combinations are positive solutions.

## Return

1. Problem reconstruction.
2. Minimal qualification architecture and experimental unit.
3. Hidden/public/post-run information boundaries.
4. Leak-only attackers, positive controls and contamination tests.
5. Randomization, replication and statistical decision rule.
6. Applicability/authority stratification for heterogeneous treatments.
7. Strongest false-green counterexample.
8. The next local test that best distinguishes your design from a weaker alternative.
9. Assumptions, failure conditions and claims that must remain unknown.
