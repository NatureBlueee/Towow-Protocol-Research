# Wave 014 — CT-001 Hidden Causal Twin

CT-001 is a minimal executable counterexample to outcome-only grading.

Two actual multi-process worlds produce the same Target state. In one, A4 is
the Target-recorded direct actor. In the other, Router suppresses A4 and an
independent Helper becomes the direct actor. A legacy evaluator reports both
as successful; a provenance-aware evaluator denies A4 exact-success credit in
the second world without denying that the requested physical state exists.

## Run

```bash
python3 run.py
python3 -m pytest -q
```

Each run writes one `causal-twin.json` under `artifacts/ct001-<opaque-pair>/`.
The artifact contains both raw world bundles and both evaluator outputs.

## Expected result

```text
state projection hashes: equal
pre-decision alpha shapes: equal

legacy:
  W_G = SUCCEEDED
  W_F = SUCCEEDED

causal:
  W_G = SUCCEEDED
  W_F = MATCHING_STATE_EXTERNAL_CAUSE
```

## Evidence surfaces

- `service_manifest`: signed process start receipts and independent public
  keys.
- `arm_native`: A4 request and pre-decision alpha shape.
- `router_native`: signed route decision.
- `helper_native`: pre-frozen plan receipt and optional Helper request.
- `target_native`: signed atomic commit receipt and provenance-free state
  projection, plus a signed authoritative readback that binds the state to the
  Target commit ID.
- `controller_private`: world intervention details, absent from A4's view.

See `CONTRACT.md` for the exact claims and non-claims, and
`ROOT-ACCEPTANCE.md` for the accepted actual artifact and claim boundary.
