# Failure history

## FH-001 — overbroad expected-label isolation assertion

- First run: `9 tests`, `8 PASS / 1 FAIL`.
- Failed test:
  `test_owner_native_outcomes_are_not_controller_expected_labels`.
- Cause: the test searched the complete trace entry for the substring `expected`.
  A legitimate coordinator request contains `expected_head` for optimistic
  concurrency control, so the assertion confused a current owner-head
  precondition with a private expected outcome label.
- Repair: search only owner service responses. Owner native responses contain
  signed exact binding and native outcome, but no expected-label field and no
  controller-supplied `CORRECT`.
- Authority, target, fence, compensation, Standing, and migration behavior did
  not change as part of this test repair.

## FH-002 — independent C attack found three false-closure paths

After the first `10/10` green run, independent Agent C bypassed three claimed
boundaries:

1. an `UNRESOLVED` Standing record could still receive current owner outcomes
   and reach `ENERGIZED`;
2. controller-built `Q@v2` config could redefine both owner and target expected
   truth, then reach `ENERGIZED` without a separately frozen O_Q act;
3. migration accepted forged schema, negative fence, bogus owner heads/receipt
   hashes/readback hash, and an invented Acceptance status.

Repairs:

- owner and target now independently fail closed on non-current Standing;
- owner and target independently compare every run against frozen CE-001 Q,
  classifying controller material change as
  `SUBSTITUTION_INVALID_FROZEN_Q`; a real O_Q material change requires a new
  owner act and separately frozen run;
- migration verifies schema, exact owner set/heads/receipt hashes, positive
  fence and coordinator epoch, actual target readback hash, exact Standing and
  the G5-bounded pending Acceptance enum;
- target persists `min_coordinator_epoch`; after takeover, old runtime epoch 1
  is rejected target-side and new epoch 2 gets only an idempotent replay.

## FH-003 — root CE-001 target-truth audit invalidated the first green model

The second-round root audit demonstrated that the v1 target could:

1. `ENERGIZE` with no owner process or owner receipt;
2. accept controller-supplied `ADVANCE_FENCE=999`;
3. verify a forged receipt against the public key carried inside that same
   receipt;
4. conflate the venue owner head with the resource fence;
5. accept controller `DEENERGIZE` intent without signed Authority loss;
6. describe a shared-store process restart too broadly as migration.

Repair:

- introduced a separate signed monotonic Authority channel and out-of-band
  target trust anchors;
- strict target now consumes current signed owner receipts, exact required
  owner set, owner heads, exact operation, reservation receipt, independent
  resource fence and Standing;
- U/D/P use canonical distinct topology closures; an operation label cannot
  select or prove a topology;
- compensation requires a channel snapshot containing owner Authority loss;
- Q and target revision are now separate (`q_id/q_version` versus
  `object_id/object_revision`);
- migration uses different source/target PIDs but is explicitly limited to
  `SHARED_DURABLE_STORE_PROCESS_RESTART`; cross-failure-domain remains
  `NOT_RUN`.

The repair does not solve a malicious transport/controller withholding a
revocation event before Authority-channel ingest. It assumes trusted bootstrap
configuration and reliable event delivery, and records both assumptions in
results and README.

## FH-004 — migration replay was produced by the wrong process

After FH-003 was green, independent C inspection reproduced two false claims:

1. the trace phase named `OLD_RUNTIME_REPLAY` was handled by the restored
   target PID because the source process had already exited;
2. the migration capsule was unsigned, so a caller could rebuild it from the
   current target state, claim `coordinator_epoch=999`, restore successfully,
   and then self-report epoch 999 on execute.

Repair:

- coordinator epoch moved into durable Authority-channel state;
- channel snapshots no longer sign a caller-selected epoch;
- channel issues only a monotonic `+1` signed takeover lease binding exact
  operation, topology, source-state hash, Authority snapshot, Acceptance and
  the shared-store process-restart scope;
- target restore verifies the lease against its trusted channel key, and
  execute accepts exactly the current epoch rather than any greater value;
- the migration harness now starts a third, separately identified
  `SOURCE-RUNTIME-RESTARTED@epoch1` PID from the shared store. That PID, not the
  restored target, returns `STALE_COORDINATOR_EPOCH_REJECTED`;
- unsigned, signature-tampered high-epoch, controller-requested epoch 999,
  stale-lease and unissued-high-execute attacks are regressions.
