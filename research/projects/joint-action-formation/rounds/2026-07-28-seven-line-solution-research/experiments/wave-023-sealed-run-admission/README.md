# Wave 023 — Sealed run admission

Wave 023 is a fail-closed **development admission smoke**, not a CE-001 run.
It hardens the gap between Wave 021's static field/profile contract and an
executable blind comparison.  It does not launch candidates, score outcomes,
compute confidence intervals, select a winner, or claim that CE-001/V1/V2 is
solved.

## Current result

The checked-in fixture may return only:

`DEVELOPMENT_SMOKE_ADMISSION_ACCEPTED_UNSCORED_NOT_EXECUTED`

and must retain:

- `comparison_status = NOT_RUN`;
- `winner = NOT_EVALUATED`;
- `comparative_evidence = NONE`.

`ACTUAL_COMPARISON_SEALED_NOT_RUN` is deliberately rejected.  This is not a
temporary naming choice: the present directory has no trusted controller/root
seal, trusted owner/principal key registry, independently derived live
delegation currentness, actual multi-replicate clone closure, binary/container
artifact store, or runtime-native Effect/Acceptance/finality receipt verifier.
Accepting an actual batch before those exist would reproduce the false-green
problem this wave is intended to expose.

## What is machine checked now

`admission_validator.py` rejects unknown keys and duplicate JSON keys, and
recomputes the contract and batch seals.  It also verifies:

- the actual Wave 021 file hash, its internal contract hash, all eight bound
  source files, and the exact machine/human Problem V1/V2 snapshots;
- a hard-pinned (not author-replaceable) full Q byte preimage and its object, Target, operation, safety, noise,
  owner Acceptance and finality coordinates;
- exactly one sealed candidate for every treatment in one family; direct
  A1–A5 and combined C1–C3 cannot be mixed;
- a closed candidate-bundle manifest that binds executable/model/prompt/console
  content hashes and rejects known case/oracle markers;
- Ed25519 integrity of the development topology witness, its world/Q/Target/
  operation binding, and U/D/P topology shape;
- world-preimage equality together with per-treatment clone, namespace and
  keyset independence;
- controller-shaped receipts containing the actual initial payload, argv, env,
  cwd, process name, file descriptors, network and endpoint inventories—not
  only profile names or declared hashes;
- semantic trigger Q/Target/operation/owner-head/Target-prefix bindings,
  preregistered event classes/interventions, exact fired count, and pre/post
  digest distinction;
- a closed budget meter ledger whose counters are recomputed, no override or
  component-level budget grant, and the Wave 021 common limits;
- A1 as `NOT_APPLICABLE` in a plural-independent (`P`) world;
- a committed exact run permutation, fixed stop/repair rule, and no premature
  CI or optional stopping;
- absence of pre-run claims for current-at-commit Authority, Target Effect,
  readback, O_Q/O_V Acceptance, or O_P finality.

These checks validate the outer development manifest and selected attack
surfaces only.  The development Ed25519 key is self-contained fixture material;
it proves fixture integrity, **not lawful Authority**.  Likewise, trigger
pre/post values are sealed digests rather than a trusted native event store.

## Isomorphic S/R twin supported by the contract

World preimages can be paired with the same non-placeholder
`shared_public_prefix_sha256`, one `twin_role = S` and one `twin_role = R` in a
single `isomorphic_twin_group_id`.  The validator requires exactly one S/R pair
with the same public prefix.  This is enough to seal the shape of the next
high-information experiment:

- **S:** exact delegation remains current at commit; Effect commits, ACK is
  lost, the runtime crashes, then status/readback recovery must establish one
  Effect and finish Acceptance/finality;
- **R:** the public prefix is isomorphic, but the Authority epoch is revoked
  before commit; the correct native result is zero Effect and `REVOKED`.

Wave 023 does not execute that twin.  A later version must add a trusted
Authority registry and commit-time signed Authority receipt, Target-native
commit/status/readback receipts, owner-native Acceptance/finality receipts, and
independent root acceptance before the twin can become comparative evidence.

## Run the admission smoke

```bash
python3 admission_validator.py RUN-CONTRACT.json fixtures/FAIR-SEALED-BATCH.json
python3 -m pytest -q -p no:cacheprovider tests
```

The attack tests mutate and re-seal manifests, rather than relying on stale
hashes to fail.  They include unknown-key, placeholder-hash, Q substitution,
launch side-channel, candidate oracle, hidden-meter, post-grader trigger,
Authority signature, clone-sharing, budget, A1 applicability, family mixing,
order, optional-stopping, and false runtime-receipt attacks.
