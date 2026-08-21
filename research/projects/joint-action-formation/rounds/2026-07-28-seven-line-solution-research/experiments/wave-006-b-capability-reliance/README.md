# Wave 006-B G4 capability-to-reliance

状态：`LOCAL_SYNTHETIC_COMPARISON_COMPLETE`

## 研究问题

本实验把四种 reliance strategy 放到同一个冻结任务
`W6-STERILE-ROUTE-SIMULATION-001`、同一 operation
`RUN-STERILE-ROUTE-SIM-v1`、同一事件序列和同一时点可见证据上比较：

1. `DECLARATION`：活动中的能力声明；
2. `LATEST_PROBE`：最近一次与 operation/key/environment/command/semantic 精确绑定的 probe；
3. `RECEIPT_HISTORY`：连续三次、带 recipient ACK 与 external anchor 的精确成功历史；
4. `SLA_RECOVERY`：SLA、当前健康、恢复责任和恢复 receipt。

策略函数只收到 `visible_snapshot`；`truth` 只交给 evaluator。没有策略得到更多未来状态，也
没有策略改变 operation、Authority 或失败。

## 冻结时序

fixture 保留共享任务的 E0–E8，并覆盖：

- probe 成功后 holder revocation 与重新授权；
- recipient key rotation；
- environment version drift 与 adapter recovery；
- delayed ACK；
- single-side partial materialization 与 compensation/recovery；
- beneficiary refusal；
- exact replay 与 same-key changed command；
- anchor fork；
- schema-compatible alias 与 material semantic change；
- `UNKNOWN / REFUSE / ABSENT`。

## 结果

22 个冻结 decision point 的聚合净值：

| 策略 | false reliance | missed opportunity | recovery steps | evidence cost | net task value |
|---|---:|---:|---:|---:|---:|
| SLA + recovery responsibility | 0 | 0 | 0 | 60.3 | 159.7 |
| Latest exact probe | 1 | 4 | 1 | 30.3 | 109.7 |
| Capability declaration | 7 | 0 | 0 | 15.1 | 78.9 |
| Continuous receipt history | 0 | 7 | 7 | 51.5 | 34.5 |

这不是“越复杂越好”：

- 在稳定低风险 case，四种策略准确率相同，`DECLARATION` 以最低证据成本单独胜出；
- 在 probe 后撤销 case，声明和最近 probe 都错误依赖；receipt history 避免 false reliance
  但恢复过慢，SLA/恢复责任在本冻结时序中同时避免错误依赖和恢复漏失；
- 连续历史并未自然胜出。它在 sudden drift 前不能预测未来，在恢复后又因三次历史门槛错过
  有效行动，成本和恢复延迟吞噬了其保守收益；
- 聚合 winner 只说明本组失败损失、证据成本与时序下的结果，不是对所有任务的普遍推荐。

最强反例是 `anchor-fork`：domain postcondition 可以实际出现，但外部锚已分叉；此时
`operation_success = true`，`safe_to_rely = false`，`business_effect_accepted = false`。
漂亮的单次 success 不能自动晋升为 capability、reliance 或业务效果。

## 四个不等式

- `operation success`：冻结 simulator 在 deadline 内到达 domain postcondition；
- `capability`：证据只支持精确 operation/key/environment 下的能力；
- `reliance`：Principal 在当前决策时点有校准后的任务分配依据；
- `business effect`：beneficiary 对精确 frozen output 独立 acceptance。

beneficiary refusal case 明确保留了“operation 成功但 business effect 不成立”。

## 运行

```bash
python3 evaluator.py --output results/baseline.json
python3 -m unittest discover -s tests -v
```

## 证据边界

这是本地合成比较。数值不代表现实故障频率、真人接受、医疗安全、商业价值或生产保证。
结果只支持 G4 的有界判断，不晋升 G2/G6/G7 或整个通爻体系。已有 monitoring、SLA、
signed webhook、transaction log 或人工责任制度若能在相同边界下解决问题，应直接采用。

