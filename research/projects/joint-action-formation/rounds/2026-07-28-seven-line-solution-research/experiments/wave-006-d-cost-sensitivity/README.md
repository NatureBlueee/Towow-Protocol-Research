# Wave 006-D cost sensitivity

状态：`PARAMETER_SCAN_AND_ANALYTIC_DOMINANCE_COMPLETE`

## 为什么需要这一轮

Wave-006-A 在 relation representation 上选择了最简单的
`A_DELIVERY_RECEIPT_ONLY`；Wave-006-B 在聚合 reliance baseline 上选择了
`SLA_RECOVERY`。这两个 winner 都依赖价值和成本权重。

本实验不重跑任务、不改变事件、不创造新成功或失败。它冻结 A/B/C 的原始结果计数，然后只
改变：

- false action / false relation 的 failure loss；
- missed opportunity value；
- evidence multiplier；
- disclosure unit cost；
- coordination operation cost；
- recovery step cost。

Wave-006-C 结果也以精确 hash 绑定到同一 shared task 分母，但不借用它改变 G2/G4 的计数。

## 扫描空间

共扫描 `7,200` 个离散权重点：

- failure loss：`0, 5, 10, 18, 30, 50`
- missed opportunity value：`0, 2, 5, 10, 20`
- evidence multiplier：`0.5, 1, 2`
- disclosure cost：`0, 0.5, 1, 2`
- coordination cost：`0, 0.25, 0.5, 1, 2`
- recovery cost：`0, 1, 2, 5`

固定 accepted task value 为 `20`。网格占比只描述这个明确采样空间，不是现实概率。

统一评分：

```text
accepted * accepted_task_value
- failure * failure_loss
- missed * missed_opportunity_value
- evidence_multiplier * (
    disclosure * disclosure_unit_cost
    + coordination * coordination_operation_cost
  )
- recovery * recovery_step_cost
```

## G2：简单 relation evidence 的结论稳健

| 策略 | 唯一胜出点 | 占全部网格 |
|---|---:|---:|
| A Delivery receipt only | 5,760 | 80.00% |
| B Dual recipient ACK | 0 | 0% |
| C ACK + explain-back + relation proposal | 0 | 0% |

A 在全部 `7,200` 点都处于 winner set：

- A 对 B 的差为 `evidence_multiplier × 2 × coordination_cost`；
- B 对 C 的差为
  `evidence_multiplier × (2 × disclosure_cost + 5 × coordination_cost)`。

所以在非负成本下，A 弱支配 B/C，B 弱支配 C。`1,440` 个 tie 点不是复杂方案产生了增益，
而是 coordination cost 被设为零；当 disclosure 和 coordination 都为零时三者完全相同。

这支持一个有界而稳健的正向结果：

> 在 Wave-006-A 已观察到的相同 task outcome、相同错误和相同恢复计数下，不物化持续关系的
> 简单现有证据组合足够；更复杂 representation 没有可由成本权重挽回的观测增益。

如果未来真实任务证明 B/C 减少了 A 没有减少的 stale reuse、false constitution 或 missed
action，必须使用新结果重开本分析；当前 dominance 不能代替那个未观察到的收益。

## G4：SLA baseline winner 明显条件化

| 策略 | 唯一胜出点 | 占全部网格 |
|---|---:|---:|
| SLA + recovery responsibility | 4,547 | 63.15% |
| Declaration | 2,421 | 33.63% |
| Latest exact probe | 170 | 2.36% |
| Receipt history | 0 | 0% |

精确 tie 为 `62` 点；winner margin 不超过 1 的 tie/近边界为 `75` 点（1.04%），这些区域不应
做强选择。

baseline 的 SLA winner 必须降级为：

> 在 failure loss 足以覆盖额外证据与协调成本时，SLA/恢复责任胜出；它不是不依赖权重的
> 全局 winner。

最清楚的转折：

```text
SLA - Declaration
= 7 * failure_loss
  - evidence_multiplier * (
      15.2 * disclosure_cost
      + 60 * coordination_cost
    )
```

baseline 其他权重固定时：

- failure loss `> 6.457`：SLA 胜 declaration；
- failure loss `< 6.457`：declaration 胜；
- 等于阈值：无结论 tie。

Declaration 与 Latest Probe 的 baseline 转折约为 `12.867`：

- failure loss 较低或 missed opportunity / evidence cost 较高时，declaration 胜；
- failure loss 较高时，probe 避免六个额外 false reliance 的价值超过其漏失和证据成本。

Receipt History 在本范围从未胜出，并被 Latest Probe 与 SLA 在采样范围弱支配。原因不是历史
“没有证据”，而是它的零 false reliance 没有抵消 `7` 次 missed opportunity、`7` 个恢复
step 与高 coordination cost。若 failure loss 超出 50 或其他策略出现当前未观察的高后果
失败，这一结论仍可翻转，因此这里只声明采样范围 dominance。

更精确地说，在本次有限网格中 Latest Probe 与 SLA 对 Receipt History 都是**严格支配**：
每一个采样点的分数都更高。G2 没有覆盖全网格的严格支配，因为零成本边界存在 tie；但当
coordination cost 大于零时 A 严格优于 B，当 disclosure 或 coordination 任一成本大于零时
A 严格优于 C。

## 稳健与脆弱

- 稳健：G2 的 A 方案在所有非负采样权重下不劣于 B/C；
- 脆弱：G4 的 SLA 与 declaration 由 failure-loss/证据成本比决定；
- 局部稳健：Receipt History 在本范围没有 winner region；
- 无结论：零 coordination 的 G2 tie，以及 G4 的 62 个精确 tie/75 个近边界点；
- 正向结果：简单方案胜出不是失败；它直接取消在该作用域重复创造复杂对象的必要性。

## 运行

```bash
python3 analyzer.py --output results/sensitivity.json
python3 -m unittest discover -s tests -v
```

## 证据边界

这里只分析已有合成结果对权重的敏感性。它不估计现实权重分布，不证明现实 failure loss，
也不把 Wave-006-A/B/C 的局部结果晋升成通爻整体结论。
