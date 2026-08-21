# CE-001 independent reference harness

This package is a **mechanism-level executable simulation**, not an empirical benchmark of Temporal, Camunda, OpenFGA, OAuth servers, OPC UA products, or any other named product.

It makes the proposed comparison concrete:

- owner services, resource market, target command ledger, target-native meter, acceptance and settlement are separate;
- four arms have independent control loops and share no candidate selector or expected label;
- lost acknowledgements, wrong-object evidence, reservation revocation, non-delegable refusal, condition formation, coordinator crash and stale-runtime replay are injected;
- the evaluator derives results from target and owner state after the run;
- source-hash, one-arm sabotage, formation ablation and truth-transplant checks are included.

Run:

```bash
python3 run_harness.py --output results.json
```

Read `RUN_REPORT.md` first. Inspect `results.json` for full action traces, owner decisions, target ledgers, effects and settlement records; `batch-results.json` contains a 50-seed fixture-order stability check.

## Important limits

The harness does **not** prove that a named mature product closes CE-001, does not model actual electrical safety or law, and does not test V2's billion-scale network, private-world discovery, ecology-level compilation, third-party externalities or cross-product semantic migration. It is a runnable falsification scaffold for the bounded episode only.
