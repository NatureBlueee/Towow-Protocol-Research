# CE-001 跨线集成硬门 v0

日期：2026-07-30  
状态：`CANDIDATE / ROOT AUDIT DERIVED / INTEGRATED RUNNER NOT YET IMPLEMENTED`

## 目的

阻止七个局部组件把相似字段直接拼成合同级成功。集成器不相信任何单线自报的
`ExactTaskSuccess / CorrectResolution / RecoveryToValue / Acceptance / Settlement`；
它只消费该线在自身作用域内有权产生的证据，再由独立 contract evaluator 重算。

## 输出命名空间

| 线 | 可进入集成器的原生输出 | 不得直接穿透的合同结论 |
|---|---|---|
| G1 | candidate、provenance、discovery denominator、handoff bytes | Commitment、Authority、Effect、Acceptance |
| G2 | constituted/understood/claimed 与 owner-attributed acts | authorized/activated 已成立 |
| G3 | C/N/E/T/V、bounded reachability、operator/remove/reverse witness | ExactTaskSuccess、合同级 recovery |
| G4 | P0/I/P1、attempt timing、reconciliation、Y_success/Y_resolution 的局部坐标 | 独立 owner Acceptance、合同级因果优势 |
| G5 | signed current Authority receipts、standing、fence、native target gate | Effect、Acceptance、Settlement |
| G6 | operation-bound occurrence、CountsTowardQ、Adoption、分 owner Acceptance、O_P finality | 迁移/历史连续性 |
| G7 | append-only history、dependency graph、reopen、runtime/capsule/epoch lineage | Authority、Effect、Acceptance 的首次创建 |

若某线当前实现无法满足本行 owner/truth 边界，集成字段写
`UNQUALIFIED_COMPONENT_OUTPUT`，不能用同名布尔值代替。

## 合同级成功唯一计算链

只有独立 evaluator 同时看到以下证据，才可产生
`CE001.ExactTaskSuccess=true`：

```text
O_Q frozen Q@v
∧ applicable-path proof
∧ each necessary owner act
∧ current G5 Authority closure
∧ O_E target actually consumed that closure
∧ exact operation Effect occurrence
∧ exact target/Q/deadline/power/duration/safety/no-other-circuit constraints
∧ distinct O_Q Acceptance
∧ distinct O_V Acceptance
∧ O_P obligation/finality after Acceptance
∧ G7 history contains the same causal lineage without rewrite
```

以下均不蕴含合同成功：

- Agent Card、ARD match、RelationVersion、workflow complete、outbox published；
- policy allow、reservation、command accepted、provider ACK；
- Effect shape match、同 service 自动生成两个 Acceptance、combined `O_Q+O_V`；
- compensation requested、capsule schema valid、旧 runtime 没有被显式观察到；
- 单线 `ExactTaskSuccess=true`。

## Owner 与进程门

- O_Q、O_V、O_R、O_S、O_P、O_E 必须有独立 state/act source；
- 同一 Python object、closure 或 private fixture 自动回答多个 owner，只能标为
  `SIMULATED_MULTI_OWNER`；
- 签名 receipt 还必须由对应 target 或 evaluator 实际消费，不能只在日志中存在；
- 同一 Unix user 的进程隔离只证明普通 interface isolation，不宣称抵御恶意本机扫描；
- Acceptance closure 必须验证 required owner set，重复同一 owner 不增加覆盖；
- O_P 不能由 O_Q/O_V Acceptance object 顺手生成。

## 比较单位：完整策略，而非孤立 primitive

合同原 A0–A5 不应被误解为互斥技术阵营。最强现有 baseline 是一个完整策略：

```text
EXISTING_HYBRID_UPPER
= 条件化选择 {
    platform-direct,
    lawfully-unified center,
    exact-delegated center,
    general model + mature stack,
    deterministic mature composition,
    bounded human institution
  }
```

它可以按 owner-owned applicability 在不同 case 选择不同现成路径。若该策略在全部 case 闭合，
就是现有技术完整解决；不能因为没有“单一 primitive arm 7/7”而否认成功。

公平比较至少包含：

1. `EXISTING_HYBRID_UPPER`：不给 candidate delta；
2. `EXISTING_HYBRID_UPPER + candidate delta`：只有存在稳定 residual 后才实例化；
3. 必要的能力移除/路径固定消融，用于定位哪项现成能力实际承重。

每个完整策略有自己的 decision executor、state、queries、recovery 与成本。共享 owner APIs、
target simulator 和 evaluator，但不能共享决策函数。

## E4 / E6 特别门

### E4

`RecoveryToValue=true` 必须同时满足：

- 原 occurrence 或损害被 target-native recovery + readback 处理；
- 撤销后的旧 Authority/fence 不能继续执行；
- 替代 partner 经过重新发现、关系/条件、Authority 与 attempt；
- 最终 exact Q 在 deadline 内完成并被 Acceptance/Settlement；
- 失败历史保留。

### E6

- source/target runtime 是不同 process/state boundary；
- target state 或 durable store 的共享范围如实声明；
- old runtime restart 必须实际发生并被新 epoch/fence 拒绝；
- capsule/source/target/history prefix 与 owner evidence hashes 验证；
- Effect 后不重复 Effect，Acceptance/Settlement 从 owner 处恢复；
- capsule 缺字段、错 Q/object、旧 epoch、history fork 必须 fail closed。

## 当前进入条件

截至当前：

```text
SEVEN_LOCAL_COMPONENT_IMPLEMENTATIONS = RUNNABLE
CROSS_LINE_SHARED_CHOOSE_ROOT = NOT OBSERVED
HOSTILE_ORACLE_ISOLATION = NOT ESTABLISHED
INDEPENDENT_OWNER_TRUTH = MOSTLY NOT ESTABLISHED
REAL_PRODUCT_EXECUTION = NOT RUN
INTEGRATED_ARM_RUNNER = NOT IMPLEMENTED
CE001_COMPLETE_SOLUTION = NOT ESTABLISHED
```

第二轮 G1/G2/G4/G5/G6 修复和 G3/G7 首轮红灯关闭前，不实现合同评分；可以先实现只拒绝
unqualified output 的集成 schema/validator。
