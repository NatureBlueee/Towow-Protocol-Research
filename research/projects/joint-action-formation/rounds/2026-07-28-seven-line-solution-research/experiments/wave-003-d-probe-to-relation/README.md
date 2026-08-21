# Wave 003-D — Probe evidence to relation state

This bridge consumes a Wave 003-B synthetic probe result and decides only what state transition that evidence
permits. It does not rerun the probe and does not infer real enterprise capability.

The key distinction is:

- a complete, buyer-witnessed bounded probe may qualify the exact synthetic probe operation;
- it does not establish the business Effect of producing backlog-worthy conclusions;
- it does not create data authorization, provider commitment, Adoption, Acceptance or Settlement.

Run:

```bash
python3 bridge.py \
  --result /tmp/t2-probe-wave-003-b/success.json
python3 -m unittest discover -s tests -v
```
