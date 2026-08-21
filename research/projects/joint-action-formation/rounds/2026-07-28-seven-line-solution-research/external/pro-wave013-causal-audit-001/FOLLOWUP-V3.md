# PRO-WAVE013-CAUSAL-AUDIT-001 — evidence update v3

This is an evidence-return follow-up. The external reviewer must independently revise its prior
judgment rather than preserve it.

Two successive fairness attacks invalidated the first two claims of label blindness:

1. semantic `case_id` and case-derived run/process/path identifiers were visible;
2. after removing those literals, the visible full-manifest hash still committed to `case_id`, so
   the two known candidate labels could recover the case by dictionary match; Python spawn also
   copied the parent CLI `--case` argument into child `sys.argv`.

All intermediate green runs are retained only as development evidence.

Current actual implementation:

- evaluator-private manifest retains `case_id` and full `manifest_sha256`;
- arm-visible view excludes both and receives an independently random `arm_binding_token`;
- owner/Target arm-facing traffic binds only that token;
- private freeze receipts, fragments and evaluator artifacts bind the full manifest;
- run/process/cwd identifiers are fixed-length digits-only;
- parent argv is sanitized before spawn, and child argv/process/cwd are recorded;
- evaluator rejects semantic labels or the evaluator-private manifest hash in arm-visible inputs.

Verification:

- 41/41 evaluator/runtime/root checks passed, including a real CLI argv-leak test;
- `ce001-run-98769954828719289991`: `SUCCEEDED`, exact/correct/safe/valid true, errors 0;
- `ce001-run-17131469301657144993`: `BOUNDED_REFUSAL`, exact false,
  correct/safe/valid true, errors 0;
- both start payloads are 1333 bytes;
- semantic labels absent;
- private manifest hash absent;
- E1/E5 two-candidate hash-oracle visible matches: 0;
- child argv is `["run.py","--opaque-arm-child"]`.

Still not covered: hostile same-user inspection, whole-run rewrite, real organizational
independence, real causal Effect, more than E1/E5, or the causal-twin attack.

Requested independent revision:

1. Which exact claims are now supported, and which remain withheld?
2. What is the strongest remaining false-positive construction?
3. What is the smallest executable label-blind causal-twin test?
4. Could mature existing technology or a lawful strong center eliminate the gap? Count that as a
   positive solution.

Do not infer real-world authority, independence, causation or V1/V2 completion.
