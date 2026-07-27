# Fieldkit Public Trace Extension v0.5

这个扩展允许把公开历史材料导入研究事件链，但故意不把回顾性材料伪装成 live Fieldkit event。

新增字段：

- `observation_status`：OBSERVED / ASSERTED / ADJUDICATED / INFERRED / UNKNOWN；
- `observability_gaps`；
- `retrospective_selection_risk`；
- `source_ids`；
- `compressed_stream_visibility`。

运行：

```bash
python import_public_trace.py ../../experiments/R7P_public_trace_pilot/coded_events.jsonl public_trace_chain.jsonl
```

导入器会校验七维、必要字段和来源，并生成独立哈希链。它不签发 Mandate，不代表 Principal Stance，也不会把公开文档转化为真实 Acceptance。
