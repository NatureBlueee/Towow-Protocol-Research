# CE-001 actual artifact binding audit

状态：`CURRENT ARTIFACTS NOT JOINABLE / CONTRACT SCORE NOT COMPUTED`

这个检查器只回答一个先决问题：

> 当前 G1–G7 的实际稳定产物，是否来自同一个冻结
> `world/run/case/Q/object/operation/owner-registry/target-registry`？

它不评价 CE-001 成功，不把手写 `qualified-e1/e6.json` 当作实际组合运行，也不因为七个
namespace 都存在就推断它们属于同一件事。

当前实际结果是 `NOT_JOINABLE_CURRENT_ARTIFACTS`，主要原因：

- G4 没有可由另一进程按 digest 消费的持久 component output；
- 七线都没有共同 `episode_manifest_sha256`、`run_root`、selected case、owner registry
  与 target registry receipt；
- object 与 operation 坐标来自各自 local world，不能靠字符串替换证明同一 target/action；
- G6 clean fragment 没有引用 G5 的 actual source artifact；
- G7 的 Effect、Acceptance 与 finality refs 不存在于 G6 actual report。

这不否定七条线的局部能力。它阻止把七套分别成立的 conformance evidence 拼成一次不存在的
composed-arm run。

运行：

```bash
python3 audit.py
python3 -m unittest discover -s tests -v
```

只有七条记录共同绑定同一个 selected case、episode manifest、run root、Q、canonical
object、operation、owner registry 和 target registry，并且 G6 精确引用 G5 source、G7
精确引用 G6 source，才返回 `JOINABLE_SINGLE_EPISODE`。即使返回该状态，合同分数仍保持
`NOT_COMPUTED`；完整成功必须由后续独立 evaluator 从 owner/target 原生日志重算。
