# 研究线 06-V2：跨权威现实效力晋升 Gate

Contract：`LINE-06-EFFECT-AUTHORITY-GATE-V2 / v1`

状态：`ACTIVE`。ACTIVE 只授权本地冻结案例、数据契约、反例和强基线比较，不表示新机制、
真人 Acceptance、现实 Effect、Settlement 或长期净价值已经成立。

本线的 target kind 是 `EXISTING_SOLUTION`，不是 `NEW_GAP`。prior-solution disposition
已解析为 `COMPOSE`：

- `ADOPT` 单权威事务、幂等 identity、目标 readback、CloudEvents、Event Sourcing、Saga、
  durable workflow 和人工审批各自已经承担的能力；
- `COMPOSE` 它们成为获得同等输入、权限、失败注入和恢复机会的强基线；
- 只在六类冻结案例显示跨权威误晋升仍无法被组合阻止时，才 `EXTEND` 一个最小
  adapter/validator；不建立新的五段事实根。

## ACTIVE：本地冻结案例

立即运行六类案例：

1. ActionAttempt 成功但目标 Effect 不成立；
2. Effect 成立但目标未 Adoption；
3. Adoption 成立但 Principal 拒绝或保持 Acceptance Unknown；
4. 精确版本被接受后发生回滚、证据失效或未来适用性撤回；
5. 同一 Operation replay 不得制造重复 Effect、Adoption identity 或 Settlement；
6. 单权威强平台能够安全压缩状态时，候选 Gate 必须旁路。

比较结果必须报告每次晋升的 authority、对象、版本、readback、负状态、Unknown、撤销、
replay identity、错误晋升和生命周期成本。Saga compensation 是语义补偿，不得写成世界必然
回到原状态；Event/workflow history 也不得替目标域 witness 或 Principal 接受。

## BLOCKED

- 真人 Principal Acceptance、后悔和重新接受；
- 未经另行授权的现实目标域写入、现实付款或 Settlement；
- 从 Harness/R5C 合成与技术证据外推跨域现实频率；
- 商业价值、长期净值与生产有效性。

## DEFERRED

- 在强平台与已核验现成方案组合通过六案例比较前，登记通爻专用 Effect mechanism；
- 自动把 Adoption、Acceptance 或 Settlement 提升为新的正式事实根；
- 用本线结果激活 scoped reopen、Router 或中心/联邦拓扑主张。

支持结果只影响 `CLM-V2-EFFECT-AUTHORITY-PRESERVATION` 的候选证据。负结果只把 Gate
降为映射规范、普通 validator 或关闭；`CLM-010` 至 `CLM-012` 等历史语义差异以及其他母线
主张均保持 unaffected。
