结论先行：G2 当前没有证据证明需要新的 Relation engine。权威感知强中心与成熟组件组合已在 Wave009 的结构化本地合成范围内同时完整通过，故该范围 `observed residual = 0`；但完整 T2/T3/T4 尚无合格共同盲测分母，因此全问题只能是 `RESIDUAL UNKNOWN / NOT MEASURED`，不能外推为无残余。

三条子线 A/B/C 已并行完成并由主线程交叉核验。全程只读，没有修改文件、运行生产或发送受限材料。

## 1. 实际任务矩阵

| 任务 | 实际材料 | 当前资格 | 对 G2 真正检验什么 |
|---|---|---|---|
| T2 企业只读试点 | raw-export/training 的 v1 被拒，经 countercondition、sandbox probe，变成 code-to-data、no-training、买方 readback 的 v2；合法动作、Authority、数据权利、witness、Acceptance 都发生变化 | `ARCHIVAL_ANSWER_LEAKAGE_REPLAY`。原文已公开反条件、probe、v2 与裁决，不能直接做冷启动评分；必须拆成 blind input 与独立 oracle。[原始案例](/Users/nature/通爻协议研究/Towow_Complete_Research_Archive_v1.2_2026-07-27/02_WORKSPACE_SNAPSHOT/Towow_A2A_Independent_Research_v0.4/real_world_protocol/04_示例案例_企业AI只读试点.md:42)、[校正](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/TASK-TRUTH-CORRECTION-001.md:26) | material change、精确版本 Stance、多 Authority 不可代行、Effect/Adoption/Acceptance 分离 |
| T3 资源请求 | 原档只是未来实验所需的样本、Principal、adjudicator、风险与回访资源清单，没有具体 S0、资源、角色、动作或权威后置状态 | `EXECUTION_RESOURCE_REQUIREMENT_ONLY`，不可计 coverage。[原档](/Users/nature/通爻协议研究/Towow_Complete_Research_Archive_v1.2_2026-07-27/02_WORKSPACE_SNAPSHOT/Towow_A2A_Independent_Research_v0.3/real_world_protocol/R7_RESOURCE_REQUEST.md:1)、[校正](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/TASK-TRUTH-CORRECTION-001.md:12) | 目前只能冻结未来任务要求，不能判断任何 relation 已成立或方案已失败 |
| T4 三方联合投标 | 三方分别持有私有能力、容量、价格与风险；需有限披露形成角色、证据、退出、评价和资源条件 | `SYNTHETIC_TASK_SPEC`；缺真实 hidden action sets、真人 stance 与跨行业迁移。M01 后续虽经审查接受为 freeze candidate，仍是 0 scoreable episode、0 方法、0 run。[PROGRAM](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/PROGRAM.md:118)、[M01 审计](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-010-x1-m01-freeze-bundle-v0/AUDIT-002.md:4) | private column、错误无解、角色/责任共同形成、异议/provenance、撤销后的 scoped reopen |
| T5 固定平台负控 | 标准 SaaS、支付或固定平台任务 | 应由平台直达或轻 adapter 获胜 | 防止把普通 workflow 任务强行物化成复杂关系 |

## 2. 为什么 participants、ACK、workflow 都不等于 Relation

最低非蕴含是：

```text
participant list ≠ role/authority agreement
delivery ≠ understanding
ACK ≠ exact-version stance
explain-back ≠ acceptance
proposal/counter ≠ Commitment
Commitment ≠ Reservation
workflow green ≠ Relation formed
Relation formed ≠ current execution authority
execution ≠ Effect ≠ Adoption ≠ Acceptance
```

T2 中参与者没有变化，但 v1 与 v2 的数据用途、合法动作、执行域、witness、退出条件完全不同；旧“原则同意”不能穿透到 v2。T4 的 crossed square 更直接：

- durable relation 成立，但预算权已撤销且没有 reservation：`G2=DURABLE, G5=DENY`；
- 没有 durable relation，但有合法 one-shot mandate 与唯一 reservation：`G2=ONE_SHOT, G5=PERMIT`。

任何统一 `green/ready` 至少错判一个。[G2/G5 设计](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/WAVE-009-G2-G5-DESIGN.md:141)

Relation 的最小语义不是某个特定产品对象，而是：

- 精确版本的 role、action、purpose、evidence、evaluation、exit/challenge；
- `ONE_SHOT / BOUNDED / DURABLE` horizon；
- 各必要 Principal 对同一版本的可归因 stance；
- source、scope、未决 opposition 和 contribution provenance；
- material change 后产生新版本，旧 stance 不继承；
- 拒绝、撤销、到期、安全退出和局部重开；
- candidate 永不自动变成 Commitment。

这些正是历史 `CAP-REL-001…005` 的异质能力，不能压成一个 content 字段。[原生线 02](/Users/nature/通爻协议研究/research/projects/a2a-reconstruction/04_audit/native_lines/02_problem_and_relation_constitution.md:11)

## 3. 方案覆盖

| 方案族 | 已覆盖 | 本身不自动覆盖 |
|---|---|---|
| 权威感知强中心 + HITL | 从原始材料提问、生成候选、比较版本、检测冲突、升级异常 | 不能替 Principal 产生 stance、授权、异议或 Acceptance；看不到的私有事实仍看不到 |
| CMMN/BPMN + HITL | CMMN 管开放、可 amendment 的 case；BPMN 执行稳定片段 | 冷启动 materiality、私有 action set、多权威 provenance、外部 Effect |
| CLM/approval | proposal、counter、合同版本、签署、撤销 | 角色/动作语法是否完整、签署者是否是真实 Authority、资源是否已预留 |
| Commitment/negotiation | propose/refuse/counter/cancel、social-state refinement | 通常要求任务、角色和消息语义已表达；协议组合也不自动可验证 |
| DCOP/column generation/Benders/CEGIS | 本地生成改善列、cut、counterexample，减少全集披露 | 假定形式化目标、接口和某种 oracle 行为；无 column 不能区分不存在、拒绝、遗漏或无权披露 |
| 开放多作者 workspace | 共同编辑、评论、版本、局部贡献 | 只有保存 owner、scope、异议与精确 stance 才是 G2 能力；“多人可编辑”本身不是关系形成 |
| 人工制度 | 能处理模糊语义、偏好、价值冲突、例外与责任 | 人员流失、口头 ACK、会议摘要压平异议、成本与不可复现 |
| 固定平台 | 在已预编译任务中直接完成 | 不应被迫进入 Relation formation |

## 4. 当前最佳成熟组合

推荐先把以下组合作为正式强基线，而不是实现新协议：

1. `authority-aware strong center + HITL`：询问、规划、冲突检测和异常升级；
2. `CMMN → BPMN`：开放 case 先保留 amendment，稳定部分再编译；
3. `CLM/versioned workspace`：保存 proposal、counter、exact version、撤销、异议与 contribution provenance；
4. commitment record 与 transactional reservation 分离；
5. private/non-enumerable action set 才启用 local oracle、DCOP/column generation；
6. append-only provenance/event log 保存原始字节、owner、head、版本与退出；
7. G5/G6 另设 Authority gate、target-domain readback，绝不由 G2 代签。

Wave009 中，B0 强中心与 B5 成熟组合在 24 个结构化 synthetic worlds 上均为 G2/G5/integration `24/24`；单独 workflow 的三个失败均为 duplicate reservation。这证明“成熟组合可能完整闭合”，也证明 workflow receipt 不是 reservation。[Wave009 结果](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/WAVE-009-SECOND-RETURN.md:122)

## 5. 为什么业内已有这些技术，仍没自动解决精确条件

必须分成三类：

- **未集成/接口未闭合**：CMMN/CLM 编译到 BPMN、policy 或摘要时丢 source、scope、opposition、exit；workflow receipt 被当 reservation；policy Allow 被当 Commitment。这是工程问题，Wave009 已给出可闭合正例。

- **前提缺失**：原始任务没表达 Principal、Authority、exit、evaluation；owner 尚未提供 stance；T3 没有实例；私有行动集没有合法查询接口。这些事实不能由 adapter 或模型凭空制造，只能通过 elicitation、HITL、local oracle、probe、readback 建立。

- **原则性不可观察**：若两个 world 的全部合法 observation 完全相同，而隐藏 stance、private column 或 opposition 不同，任何中心、协议、模型或人工评审都不能同时做对。只能新增合法 observation、改变环境，或保持 `UNKNOWN/DEFER/SAFE_EXIT`。这不是“缺一个新协议”。

因此：

```text
R(Wave009 structured synthetic) = 0 observed
R(full T2/T3/T4/M01) = UNKNOWN / NOT MEASURED
```

待检验 residual candidates 只有：

- 冷启动辨别参数更新、同义改写与 Authority-relevant material change；
- 跨 CLM/CMMN/workspace/BPMN/policy 无损保留 provenance、opposition、version、exit；
- private column 在真实拒绝和策略遗漏下是否相对安全摘要/强中心提高召回或减少披露。

它们尚不是已证明的新机制缺口。

## 6. 下一项可证伪实验

先排除 T3。建立一个 fresh T2-blind family 和一个 fresh T4-held-out family，truth owner、solver、evaluator 分离。

最小 paired worlds：

- 语义等价改写 / 真正 data-use material change；
- ACK / exact-version stance；
- ACCEPT / 局部 opposition；
- Principal 签署 / controller substitution；
- private column absent / exists；
- column exists / owner refuses or withholds；
- active / scoped withdrawal；
- one-shot / bounded / durable。

四个公平 arm：

- 权威感知强中心；
- 上述成熟组合；
- 结构化人工制度；
- 仅在观察到残余后加入的 Relation candidate。

关键指标：

- material-change recall 与 false reopen；
- stale-stance penetration；
- feasible-path recall 与 false infeasible；
- disclosure 与策略遗漏校准；
- provenance/opposition round-trip retention；
- stale reuse、exit residual、over-reopen；
- migration loss 和全生命周期成本。

双向 falsifier：

- 如果强中心和成熟组合在相同合法观察下稳定失败，而人工或候选在不增加 Authority、披露和预算的情况下跨两个任务族及迁移通过，才建立非零 residual。
- 如果强中心或成熟组合跨两个任务族、fresh holdout、迁移和攻击全部通过，移除新 adapter 后结果不变，则“必须新机制”被证伪，G2 应落为组合配置/conformance profile。

Wave006 说明测试设计必须防止 evaluator 不读 relation evidence、候选自报 trace、按标签计费等伪成功。[Wave006 失效](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/WAVE-006-AUDIT-INVALIDATION.md:8)

## 7. 失败边界

- Wave007 B2 只支持受信 parent、本地合成 JSON-RPC 下的 one-shot/bounded-reuse 差异；不是独立实现、真人认领或 hostile same-UID 隔离。[Wave007 状态](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/WAVE-007-AUDIT-STATUS.md:221)
- Wave009 是显式结构化、单进程、受信 parent 的局部正例，不是自然语言、独立成熟产品、分布式线性一致性或一般 V1/V2 证明。
- M01 后来的精确审查只接受其为 freeze candidate；没有 owner signature、solver、runner、coverage 或方法晋升。
- T2 不可直接冷启动评分；T3 不可评分；T4 尚无真实主体与跨行业迁移。
- 原则性不可观察不能用 hash、签名或新协议消除；签名只能证明已经提交的字节。

## 8. 迁移、停更、格式与锁定审计

外部当前状态查询被取消，因此以下以仓库 2026-07-28 已登记的一手来源扫描为基础；具体 release、CVE、许可和商业条款在采用前仍需刷新，不能视为今日 live-confirmed。

| 族 | 主要风险 | 采用控制 |
|---|---|---|
| OMG CMMN/BPMN/DMN | 标准成熟，但引擎通常只移植标准子集；vendor extension、human-task/history/migration 易损 | `ADOPT` 标准 schema、`WRAP` runtime；保存标准模型、原始事件和双向 conformance replay |
| CLM | 正文可导出不等于 approval、owner、revoke、opposition 可迁移；SaaS/e-sign/webhook 锁定 | 自持 canonical clause/version/stance/event export；保留最小签署与 approval ledger |
| FIPA/commitment | 核心稳定但低活跃，任务与 message semantics 需预表达；协议组合不自动安全 | 保存 typed conformance traces；有界 commitment kernel 可低成本重实现 |
| DCOP/column/solver | objective、column、cut、privacy proof 多为项目自定义；solver 许可和回调语义可能锁定 | solver-neutral schema、oracle replay、可替换 provider；最小 local oracle 可自持 |
| 多作者 workspace | 导出常丢 comments、suggestions、身份、scope、permission 与 unresolved thread | append-only event export、content-addressed version、round-trip loss gate |
| 强中心/Agent framework | 模型、API、session 与编排层漂移快 | 模型只作可替换 planner；权威事实留在自持 ledger；升级前后 replay |
| 人工制度 | 人员流失、口头同意污染、制度漂移 | owner map、精确版本签署、异议/退出模板、交接和替补演练 |
| 完整组合 | 最大风险是接口升级顺序与第二事实源 | 每层双向导出、版本 pin、故障恢复演练；adapter 只验证/传递 owner truth |

仓库已有扫描同样建议：标准优先 `ADOPT`，引擎 `WRAP` 并保留 export/conformance；只有强基线在合格任务上留下稳定断点才 `INVENT`。[现成方案扫描](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/WAVE-001-EXISTING-SOLUTION-SCAN.md:139)

本轮最重要的行动变化是：不要继续补 G2 概念或薄 adapter。先把 T2-blind、fresh T4 和迁移 round-trip 变成有效分母，直接运行强中心、成熟组合与人工制度；它们完全解决就是 Wave010 G2 的成功。

