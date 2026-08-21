# T5 Collapse-safe negative control

This synthetic negative control asks a method to buy a standard SaaS SKU through a platform that already
provides catalog, approval, payment, provisioning, invoice, audit and authoritative readback. The evaluator
runs a deterministic platform state machine; a method label or claimed truth source is not enough.

The correct solution may be entirely existing-platform-native. Passing this task is evidence that a broader
Towow composition can collapse to zero new protocol mechanism when the original problem is already solved.
It is not evidence about real purchasing, payment providers or production reliability.

Run:

```bash
python3 evaluator.py --submission fixtures/platform-direct.json
python3 evaluator.py --submission fixtures/stateless-adapter.json
python3 -m unittest discover -s tests -v
```

`FIRST-EVALUATOR-FAILURE.md` records why the label-based V1 evaluator was invalidated.
`SECOND-EVALUATOR-FAILURE.md` records why V2's self-attested adapter and injected
failure terminal were invalidated. V3 only accepts a hash-bound bounded JSON
transducer and derives adapter behavior from its execution trace.
