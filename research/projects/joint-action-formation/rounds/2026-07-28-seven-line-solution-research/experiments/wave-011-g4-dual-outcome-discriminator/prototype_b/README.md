# Prototype B：最小 paired-world primitive runner

状态：`INTERNAL IMPLEMENTATION PROTOTYPE / NO ORACLE SCORE / NOT G4 EVIDENCE`

这个目录只验证 Wave 011 runner 的几个承重接口，不提供 private oracle，不比较 strong
center，也不主张真实覆盖率。

## 已实现边界

- `primitive_service.py` 返回 owner/provider 的原始 revision、policy、receipt、lease、
  submit 与 operation-ledger response。响应中禁止
  `head_current`、`fenced`、`authoritative`、`safe_to_rely` 等预裁决字段。
- `mature_composite_worker.py` 是由 runner 用 `python3 -I` 启动的独立进程。它只通过
  JSON-lines broker 调用 primitive，不读取 fixture、world ref、隐藏执行条件或 evaluator。
- worker 先冻结 `P0`，再实际请求 Authority 与 reservation，之后冻结 `P1`。形成动作不回填
  `P0`。`Y_success` 与 `Y_resolution` 是独立字段；`Y_effect` / `Y_acceptance` 明确保持
  `NOT_PREDICTED_BY_G4`。
- response-lost 分支实际执行 `submit → read_operation_status → reconcile_operation →
  read_operation_status`。测试断言 effect count 仍为 1，不能用 label-match 冒充恢复。
- broker 逐次记录 source、latency、response bytes 与 disclosure class。

`fixtures.py` 提供 3 类、共 3 对最小 executable worlds：

1. `PASSIVE`：只读 transcript 相同，worker 保持 `ABSTAIN`；
2. `ACTIVE_QUERY_COMMITMENT`：初始读取相同，reservation 的 raw owner response
   `GRANTED/REFUSED` 分流；
3. `FULL_LAWFUL_INTERACTION_EQUIVALENT`：在冻结 decision 前，全部允许交互和响应相同；
   隐藏依赖相反。这个 pair 只演示交互量词边界，不携带 scorer。

## 运行

从本目录执行：

```bash
PYTHONPYCACHEPREFIX=/tmp/wave011-g4-prototype-b-pycache \
python3 -m unittest -v test_runner.py

PYTHONPYCACHEPREFIX=/tmp/wave011-g4-prototype-b-pycache \
python3 runner.py
```

## 尚未实现

- 没有 private oracle、truth-owner evaluator、confusion matrix 或 success/resolution score；
- 没有 `Y_effect` / `Y_acceptance` owner；worker 明确不从 processor readback 推出它们；
- hard pair 的交互等价只覆盖 fixture 明确允许的 pre-decision API 与 horizon；
- 这是单一 mature-composite worker 原型，不是独立 strong center；
- 未覆盖真实 Authority、真实支付、生产 provider、并发 race 或 hostile process isolation；
- deterministic latency 是 broker 成本记账形状，不是现实 latency 测量。
