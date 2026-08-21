结论先说：Wave010 现有 `7/7` 不能继承。G7 当前状态应记为：

```text
G7_TASK_STATUS = UNKNOWN_NOT_RUN
NOVEL_PROTOCOL_RESIDUAL = NOT_DEMONSTRATED
BEST_CURRENT_CANDIDATE = MATURE_COMPOSITION
```

它最多证明：如果一个完美、及时、如实的 owner query 已经给出 `CURRENT/REVOKED`，预置策略能在两个已知 T6 world 输出预写 closure。它没有证明 dependency planner、低成本局部重开、真实恢复或跨平台移植。

## 实际任务

G7 不是“workflow 出错后重跑”，而是：

> 对一条已经正确形成、授权、执行和接受的路径，只编译稳定子图；重复运行时生成可回源的最小充分 Context，以 current owner evidence 判断其是否仍适用。漂移后，在不改写历史的前提下选择继续、阻断、恢复、局部重开、全局重开或人工 amendment，并使第二次运行成本下降且错误不增加。

原始价值包括 Context Compiler、稳定子图编译、Defeater 依赖传播和 Evidence Closure，而不是维护一张漂亮的依赖图。[G7 native dossier](/Users/nature/通爻协议研究/research/projects/a2a-reconstruction/04_audit/native_lines/07_runtime_and_evolution.md:21)

T6 的正式分母是 R1–R8：降本不增错、offline 不等于规范失效、撤销保留无关动作、证据失效不改写历史、目标变化返回关系构成、隐藏依赖进入 Unknown/阻断/人工、高耦合允许全局重开、Context/history 可移植。[PROGRAM](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/PROGRAM.md:150)

## 现有结论重审

- Wave006：G6/G7 端到端结论已经无效；策略能读取答案、忽略撤销并代替其他 Authority 签名。仅保留 signer ladder 的 `4/4 rejected` 窄证据。[Wave006 invalidation](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/WAVE-006-AUDIT-INVALIDATION.md:64)
- Wave007：A2/B2/C2 的 `52/52` 支持 attempt-time idempotency、current-head binding、L3/L4 分离等局部合成修复；不是 blind holdout、独立实现或生产恢复。[Wave007 audit](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/WAVE-007-AUDIT-STATUS.md:221)
- Wave008：没有新增 G7/T6 证据。
- Wave009：明确仍是 `T6 MUTATION REPLAY SPEC / NOT RUN`，缺合格 base trace 和 oracle dependency graph。[Wave009 design](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/WAVE-009-G4-G6-G7-DESIGN.md:156)
- Wave010：只是 `4 worlds × 9 scripted arms` 的同研究者开发夹具，7 个 gates 明确不是 PROGRAM coverage。[Wave010 synthesis](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/WAVE-010-G6-G7-SYNTHESIS.md:177)

对 T6 R1–R8 的真实覆盖是：

| 要求 | 当前状态 |
|---|---|
| R1 重复降本不增错 | `NOT_RUN`，没有 cold-vs-repeat 成本 |
| R2 offline 与规范失效 | `NOT_RUN` |
| R3 撤销只影响依赖闭包 | 单个 oracle-backed pair 的开发演示 |
| R4 证据失效、不改历史 | `NOT_RUN` |
| R5 material goal change | `NOT_RUN` |
| R6 hidden dependency | 支持“无观察时不可区分”的负结果；完整 Unknown 路由未运行 |
| R7 高耦合诚实全局重开 | `NOT_RUN` |
| R8 Context/history 跨 runtime | `NOT_RUN` |

## 为什么 7/7 不成立

模拟器的 broker 直接把 private truth 暴露为方法输入：

```python
world["truth"]["dependency_query_response"]
```

随后策略把 `REVOKED` 直接映射为硬编码的三节点 closure；它没有查询图、遍历依赖或处理新的图形。[Simulator](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/WAVE-010-G6-G7-SIMULATOR.py:96)

此外：

- 只有 `CURRENT/REVOKED`，没有 `UNKNOWN/REFUSED/STALE/LOST/CONFLICT`。
- strong-center 与 mature-composition owner-query arms 使用完全相同 profile，所以“等价”是构造出来的。
- `recovery_succeeded` 只是“没有 unsafe、没有漏节点”，没有执行重新授权、迁移、恢复和目标域 readback。
- 恢复步数是常量，不来自实际 operation log。
- 没测 Context sufficiency、history portability、connector migration 或 dependency maintenance cost。
- 当前文档自己承认 owner query 可能只是把 private oracle 包装成 API。[Wave010 residual boundary](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/WAVE-010-G6-G7-SYNTHESIS.md:246)

## 指标与安全边界

设真实 affected closure 为 \(D^*\)，方法提出的 closure 为 \(\hat D\)。

- `unsafe_continuation_rate`：漂移后仍被实际 admission/commit、但至少一个承重 prerequisite 已 `REVOKED/STALE/REFUSED` 或未获安全证明的动作，占应阻断动作的比例。
- `missed_reopen_rate = |D^*-\hat D|/|D^*|`。
- `over_reopen_rate`：无关但被阻断/重审节点的价值权重，占全部未受影响价值。
- 恢复成功：取得新 current head/授权，完成必要 migration/recovery，重新通过执行 Gate 和目标域 readback；不能以 workflow green 代替。
- 历史保真：旧 Effect、Acceptance、拒绝、Unknown、失败和原始版本仍可重建；Defeater 只能追加 future-applicability，覆盖或删除为硬失败。
- Context sufficiency：目标 runtime 仅依赖导出 bundle 即可重建同一安全判断；缺少承重 binding 时必须 fail closed。
- `reuse_surplus = cold reformation cost saved - assurance tax - drift/error/opportunity loss`。

必须分开三种结果：

- `SAFE_BY_BLOCKING`：零 unsafe，但靠全局阻断。
- `SAFE_RECOVERABLE`：真正恢复到合法可继续。
- `LOW_COST_SCOPED_REOPEN`：安全、零漏重开，同时显著减少误重开、等待、人工和总成本。

现结果中 conservative/center/human 的安全来自全局重开；local arm 反而有 `1 unsafe、2 missed、1 over-reopen`。owner-query 的精确结果又依赖 oracle，故尚无 `LOW_COST_SCOPED_REOPEN` 证据。

## 公平比较与最佳组合

| 方法 | 最强覆盖 | 主要边界 |
|---|---|---|
| Immutable contract + 人工 amendment | 历史保真、高后果、高耦合安全兜底 | 慢、误重开多、重复成本高 |
| Durable workflow/migration + telemetry | 高频稳定流程、retry、replay、运行恢复 | 不拥有 Authority、Acceptance 或 hidden dependency truth |
| Dependency/Defeater planner | 显式、稀疏、fresh head 可查时的局部闭包 | hidden/stale/refusal；图维护成本 |
| 权威感知强中心 | 查询、组合、编排和统一运维 | 同信息下不能突破不可区分性，不能代签 owner truth |

当前最佳候选是成熟组合：

```text
immutable RelationVersion / append-only history
+ durable workflow / migration / causal idempotency
+ truth-owner readback 与 signed current-head adapter
+ dependency/Defeater closure planner
+ UNKNOWN/REFUSED/STALE 时 broad block 或 global reopen
+ material goal、高耦合、高后果分支的 Principal amendment
+ 强中心作为 lawful coordinator，而非 truth owner
```

这与 Wave009 的成熟组合判断一致；依赖完整、current head 可查、readback 可用时，现成组合完整通过就是通爻的正向解，不需要新协议。[Wave009 mature composition](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/WAVE-009-G4-G6-G7-DESIGN.md:47)

## Residual 判断

当前没有被证明的 Towow-specific protocol residual。

真实未闭合的是一个条件问题：

> 能否在不吞并 owner 权威的前提下，以可接受的披露、等待、人工、维护和迁移成本，获得 fresh、可认证、语义充分、跨平台保真的 current-head 与 dependency observation？

它最终可能是：

- 成熟 API/adapter 与 conformance layer 的实现责任；
- 组织或采用成本；
- owner 不愿或不能表达依赖；
- 信息论上的永久 Unknown；
- 或尚未证明的新机制缺口。

若成熟组合在两个异质任务族和一个 held-out migration 上做到零 unsafe、零漏重开、历史零改写，Unknown 安全退化，且相对全局重开减少误开和总成本，那么 residual 就是零，应直接 `ADOPT/COMPOSE/CLOSE`。

行业技术已经存在但尚未闭合，不是因为缺“黑技术”，而是当前实验把最承重的 owner query、closure computation 和迁移语义保真作为假设直接注入了，没有让这些组件在同一合法观察、真实失败和成本分母上闭合。

## 可运行的 T6 held-out replay

1. 独立 base producer 从至少两个任务族生成真正完成、authority-valid、五层 readback 闭合的 fresh base traces；公开答案泄漏的 T2 不能是唯一 base。
2. 分离 base/history、Authority/current-head、dependency、Effect/Acceptance、Context/migration 与 scorer 六个 truth owner；禁止共享 mega-oracle。
3. Dependency API 只返回绑定 owner、edge/subject、graph version、head/epoch、freshness、purpose 和签名的原子状态，不返回 expected closure。
4. 必含 `CURRENT/REVOKED/UNKNOWN/REFUSED/STALE/LOST/CONFLICT`，以及模型回归、offline/identity change、证据失效、goal change、hidden edge、高/低耦合、不可逆 in-flight、恢复失败、Context 缺失和 connector migration。
5. 同条件运行上述四类方案、成熟组合、human arm、always-continue、global-stop 与 T5 platform-direct 负控。
6. 方法先提交 repeat/context plan，再注入 committed drift；broker 必须真正执行 continue/block/recover/reopen，不能按自报动作评分。
7. 声称恢复必须实际取得新 head/authorization、完成迁移并重新 readback；跨 runtime import 成功本身不算 portability。
8. 先运行 stale replay、truth transplant、hidden-edge delete、shared-root/leaf swap、history overwrite、migration field-drop、all-stop/all-continue 攻击，再启用评分。
9. 逐项报告 T6 R1–R8、上述指标、Pareto frontier 和分布敏感性；all-stop 最高只能得到 `SAFE_BY_BLOCKING`。
10. 若成熟组合或强中心打平且更便宜，关闭专用 planner；这是实验成功，不是负结果。

正式 X2 合同已经给出正确的 G7 oracle、隐藏依赖和报告边界，但当前仍是 `X2_WORLDS=NOT_FROZEN / X2_RUNNER=NOT_IMPLEMENTED / X2_RESULT=NOT_RUN`。[X2 G7 contract](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/WAVE-010-X2-INPUT-CONTRACT-CANDIDATE.md:588)

本轮只读完成：未修改文件、未运行生产。

