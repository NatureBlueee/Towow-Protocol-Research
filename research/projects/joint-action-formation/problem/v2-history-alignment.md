# Problem v2 历史继承与激活准备审计

Audit：`HIA-JOINT-ACTION-FORMATION-V2`

绑定：`PRB-JOINT-ACTION-FORMATION / v2`

状态：`REVIEWED`

建议：`READY`

## 一、结论

V2 可以进入用户激活决定，但本审计不替用户激活它，也不证明通爻、NAC、PFE、CRA 或任何
组合机制现实有效。

审读确认 V2 没有重写 V1。它通过四份前序材料的精确 SHA-256 保留 V1，只把容易被独立
研究线遗漏的共同底座显式化：Intent 入口不产生权威、海量异构私有网络、预编译制度与开放
形成共存、有界机制独立推进、三个分析尺度并列、人的参与重新配置，以及非形成结果的独立
价值。

本轮先进行了三个隔离的只读审查：语义审读、39 项能力继承核对和激活门审查。它们由同一
研究环境中的 Agent 完成，不构成外部独立经验验证；其作用是发现文本与治理闭包中的遗漏。
审读发现的三项共享底座缺口已经作加法式修订：

1. 显式并列 `AgentExecution / RelationEpisode / RelationEcology`；
2. 明确人的参与目标是按权威、价值与风险重新配置，而不是最小化人工；
3. 明确保留 `Clarification / Protective Contraction / Reject / Defer` 的独立价值。

## 二、覆盖口径

逐项覆盖只评价 V2 ProblemContract 和其人类说明的显式展开，不把 NAC profile、七条研究线
或被引用的 V1 审计冒充 V2 正文内容。因此覆盖计数仍为：

| V2 问题文本覆盖 | 数量 | 含义 |
|---|---:|---|
| `EXPLICIT` | 22 | V2 或其精确继承的 V1 中存在可定位的现实区别或失败边界 |
| `PARTIAL` | 10 | 有相关问题，但原行为、owner、实验或移除失败仍不充分 |
| `ABSENT` | 7 | V2 问题正文不展开，必须由独立机制、研究线或系统设计继承 |

计数与 V1 相同不表示 V2 没有增量。V2 新增的是跨能力的共享研究底座，而不是把更多机制
塞进一个总问题。`ABSENT` 也不表示拒绝或删除：它可能正是避免大一统问题定义的正确位置。

## 三、逐项去向

| Capability | 档案状态 | V2 覆盖 | 当前去向 |
|---|---|---|---|
| CAP-DISC-001 | TRANSFORMED | PARTIAL | 任务相关投影与披露遗漏回归 |
| CAP-DISC-002 | PARTIAL | ABSENT | HDC/FHRR 可替换 provider 与角色交换反例 |
| CAP-DISC-003 | PARTIAL | ABSENT | MEC-NAC 跨模型锚点独立研究 |
| CAP-DISC-004 | PARTIAL | PARTIAL | 渐进披露预算、provenance 与重建风险 |
| CAP-DISC-005 | PARTIAL | ABSENT | SEEK/OFFER 方向性及错误互配反例 |
| CAP-DISC-006 | TRANSFORMED | PARTIAL | 任务充分性而非字段完整性 |
| CAP-DISC-007 | PARTIAL | ABSENT | typed boundary response 与错误提升测试 |
| CAP-REL-001 | PARTIAL | EXPLICIT | 参数、关系、条件创造与目标改写 |
| CAP-REL-002 | PRESERVED | EXPLICIT | material change 与旧立场失效 |
| CAP-REL-003 | PARTIAL | EXPLICIT | 多来源、范围、版本与贡献回放 |
| CAP-REL-004 | LOST | ABSENT | 恢复本地 column/counterexample owner |
| CAP-REL-005 | PRESERVED | EXPLICIT | 候选不得穿透 Authority Gate |
| CAP-FORM-001 | PARTIAL | PARTIAL | typed Unknown 到探问、形成或退出 |
| CAP-FORM-002 | PARTIAL | EXPLICIT | S0、Q、operator 与反事实消融 |
| CAP-FORM-003 | PARTIAL | PARTIAL | 拒绝、countercondition 与策略操纵 |
| CAP-FORM-004 | TRANSFORMED | EXPLICIT | 现实 probe、环境绑定与 readback |
| CAP-FORM-005 | PRESERVED | EXPLICIT | 机制路由、稳定编译与局部重开 |
| CAP-CAP-001 | PRESERVED | EXPLICIT | 权限、环境、资源和版本化能力 |
| CAP-CAP-002 | PARTIAL | ABSENT | prospective holdout |
| CAP-CAP-003 | PRESERVED | EXPLICIT | producer 与目标域证据分离 |
| CAP-CAP-004 | TRANSFORMED | EXPLICIT | 过期、Defeater、漂移与恢复 |
| CAP-CAP-005 | PARTIAL | PARTIAL | 组合依赖、容量与共享资源 Gate |
| CAP-AUTH-001 | PRESERVED | EXPLICIT | Principal 与 Agent Entity 分离 |
| CAP-AUTH-002 | PRESERVED | EXPLICIT | 身份、能力、Mandate 与执行非蕴含 |
| CAP-AUTH-003 | PRESERVED | EXPLICIT | 精确版本 Stance |
| CAP-AUTH-004 | PRESERVED | EXPLICIT | Commitment 与 Reservation 分离 |
| CAP-AUTH-005 | PARTIAL | PARTIAL | 第三方 Standing 与 recourse |
| CAP-EFF-001 | PRESERVED | EXPLICIT | Attempt 与 Effect 分离 |
| CAP-EFF-002 | PRESERVED | EXPLICIT | authoritative readback |
| CAP-EFF-003 | PRESERVED | EXPLICIT | Effect、Adoption、Acceptance、Settlement |
| CAP-EFF-004 | PRESERVED | EXPLICIT | 撤销、争议和负状态保存 |
| CAP-EFF-005 | PRESERVED | PARTIAL | 幂等 identity 与重复副作用 |
| CAP-RUN-001 | PARTIAL | PARTIAL | Problem、Design、Engineering IR |
| CAP-RUN-002 | PARTIAL | ABSENT | 最小充分 Context Compiler |
| CAP-RUN-003 | PARTIAL | EXPLICIT | 形成期与编译运行期 |
| CAP-RUN-004 | TRANSFORMED | EXPLICIT | Defeater 依赖闭包与 scoped reopen |
| CAP-RUN-005 | PARTIAL | EXPLICIT | Evidence Closure |
| CAP-RUN-006 | PARTIAL | PARTIAL | Router 冷启动与 false collapse |
| CAP-RUN-007 | PRESERVED | EXPLICIT | 网络拓扑、权威拓扑与机制选择分离 |

完整 assessment 与 preservation requirement 以
`research/projects/joint-action-formation/problem/v2-history-alignment.json` 为准。

## 四、仍未恢复但不阻塞 V2 的能力

最重要的未恢复项仍是 `CAP-REL-004`：主体在私有世界生成候选，只提交改善当前解的最小
column 或 counterexample，而中心没有完整行动集时不得推导“无解”。它仍是 `LOST`，
V2 提到局部私有网络不能把它改写成已经恢复。

另外三项需要明确 owner：

- `CAP-DISC-007`：cut、witness、column、Unknown、refuse 与 countercondition 的类型化响应；
- `CAP-CAP-002`：干预前冻结 Capability Claim，并在未见任务上做 prospective holdout；
- `CAP-RUN-002`：可回源、任务相关的最小充分 Context Compiler。

这些是后续研究线或机制 profile 的恢复责任，不要求 V2 问题定义自己实现它们。

## 五、激活证据闭包

正式激活不能只绑定 `v2-candidate.json`。激活 bundle 同时冻结：

1. V2 candidate JSON；
2. V2 candidate Markdown；
3. V2 inheritance audit JSON；
4. V2 inheritance audit Markdown；
5. canonical capability matrix。

权威路径为：
`research/projects/joint-action-formation/problem/activation/v2.json`。

用户若决定激活，决定必须使用机器动作 `ACTIVATE_PROBLEM`，同时绑定 candidate 与 activation
bundle 的精确路径和 SHA-256。任何一份材料变化都会令旧决定失效。这样避免 candidate 与
audit 相互记录完整哈希形成循环，同时防止在用户决定后静默改写审计证据。

## 六、本审计不能说明什么

- `REVIEWED / READY` 只说明 V2 已达到提交用户决定的条件；
- 它不等于 V2 已经 `ACTIVE`；
- 它不证明七条问题家族必须全部同时运行；
- 它不证明 NAC 或任何历史机制成立；
- 它不把同一模型环境的三次审读算作三份独立证据；
- 它不允许从候选问题直接执行现实 Effect、激活场景或晋升稳定主张。
