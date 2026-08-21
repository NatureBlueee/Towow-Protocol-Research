# Wave 009 — 七线第二返回：现成组合的正结果与完整链缺口

日期：2026-07-29  
状态：`SECOND RETURN / LOCAL SYNTHETIC / ATTACK-RECHECKED / NO FORMAL PROMOTION`

## 本轮最重要的改变

这一轮没有把“通爻是否独占”当作成功判据。相反，它得到两个正向结果：

1. 在 G1 冻结合成矩阵中，优化强中心与 Router 因果等价，以相同成本、披露和安全覆盖全部
   当前可发现分母；这取消了在该矩阵中为 Router 制造独占优势的必要。
2. 在 G2+G5 冻结 crossed square 中，direct center 与由签名、workflow、policy、
   commitment、事务 reservation、HITL 和 readback 组成的 existing-component path，都
   完整重建当前有界真值；当前 11 项 residual matrix 没有观察到需要 B6 新机制的残余。

这两项都是通爻的正向成果。它们说明成熟能力在条件明确、truth owner 正确、接口闭合时可以
成为方案本身，而不只是“需要击败的基线”。

但它们还不是 V1/V2 完整解。完整问题最承重的困难，已经从“缺哪项技术”缩到：

> 一个组件的局部输出，何时有资格成为下一组件的输入；这个跨越是否保留了 Principal、
> Authority、version、semantics、target truth、dependency 与 lifecycle value。

## 为什么它们都有，却没有自动解决原问题

现有组件停止在不同的条件化合同：

| 组件/制度 | 能够直接给出的局部合同 | 不自动蕴含 |
|---|---|---|
| ARD/catalog/registry | 已表达、可索引资源的发现候选 | query genesis、未声明 Intent、真实可用性 |
| A2A/MCP/消息层 | 已知对象间的传输或调用 | Principal 意愿、Authority、成功后的现实效力 |
| workflow/case management | 已预编译状态与转移的运行 | 新关系是否成立、外部世界是否改变 |
| policy/IAM | 给定事实与当前策略下的 Allow/Deny | Mandate、Commitment、Reservation、Acceptance |
| transaction/reservation ledger | 一个合法 proposal 对资源的原子占用 | 关系 materiality、目标域 Effect |
| event/outbox/history | 本地命令和事件的可恢复记录 | Adoption、Acceptance、Settlement、隐藏依赖 |
| target-domain readback | 某一权威域中的当前事实 | 其他权威域的认领与长期价值 |

难点不是组件不存在，而是这些局部合同之间存在“非蕴含跨越”。如果跨越靠 controller
猜测、同名字段或 workflow green 补齐，组合会制造伪闭环；如果每次跨越都由相应 truth
owner 产生可版本化、可失效、可拒绝的证据，成熟组合就可能闭合完整问题。

## 三类剩余问题

### 1. 工程闭合

包括 exact bindings、freshness、replay、atomicity、causal identity、idempotency、
target readback、跨进程稳定身份与恢复。这些原则上可以由成熟工程组合解决；本轮 G2+G5
已经在单进程合成模型中给出一个正例。

### 2. Principal / Authority 边界

披露、立场、授权、承诺、撤销、Effect、Acceptance 和 Settlement 不能由中心因为“逻辑上
合理”而代签。强中心可以规划和编排，但它必须查询或等待真正 owner。这个边界不要求联邦
拓扑，却要求事实所有权不被计算中心吞并。

### 3. 信息论不可区分

若两个 world 的全部合法 observation 完全相同，而隐藏机会、依赖或 Principal stance
不同，任何中心、协议或模型都不能同时做对。解决方法只有三类：

- 创建新的合法 observation：澄清、probe、local oracle、code-to-data、readback；
- 改变环境，使 material variable 可声明或可查询；
- 保持 `Unknown`，并采用 bounded block、broad reopen 或 human discovery。

这是当前最强理论反例。它不证明通爻需要新协议；它规定任何完整方案必须满足的信息条件。

## G1：搜索前的问题形成与发现

### 结果

实验：
[`experiments/wave-009-g1-query-genesis/`](./experiments/wave-009-g1-query-genesis/)

- 22 个冻结合成 world；
- `L=14`，`D_actual=10`，holdout `H=10`；
- optimized strong center：`10/10 recall`、`10/10 robust safety`；
- Router composition：`10/10 recall`、`10/10 robust safety`；
- 两者 cost、latency、leakage 相同，不报告 Router 优势；
- 31/31 tests、11/11 report gates 通过；
- public index、local projection、private predicate 和 reciprocal probe 分别保留其有界贡献。

### 攻击带来的真实收窄

首轮实现曾把父进程预结构化目标的签名误称为 query genesis，也把同进程 gateway 误称为
候选只能看到 vague seed。多轮同一攻击者复核迫使实现改成：

```text
vague value seed
→ Principal clarification
→ candidate-authored query draft
→ Principal acceptance
→ signed SemanticQuery
```

最终 claim 只属于 cooperative、non-reflective candidate 对 public logical API 的使用。
Python 同进程反射能够访问 parent hidden world，所以：

```text
hostile_same_process_isolation = false
```

它不是安全隔离结论。

此外，第二次最终复核发现 executable seal 的 imported callable alias 与跨进程稳定性缺口；
最终修复绑定 consumer 实际引用的 imported aliases，并 canonicalize code constants、
defaults 与 kwdefaults。不同 `PYTHONHASHSEED` 的新进程现在产生相同 preimage；module/class
binding 被替换会使旧 bundle 失效。instance-level shadow、直接替换 verifier 与同权限恶意
进程仍明确不在 trusted-parent threat model 中。

### 结论

G1 支持一个有界正结果：当 query 可由 Principal 澄清和接受、且 local oracle 合法可查时，
强中心已经能够完整解决当前发现矩阵；ARD/RAG 仍只承担已表达对象的局部发现。这里未证明
真实 Principal、开放世界 query genesis 或外部 Effect。

Pro 独立复核暴露了一个必须追加的 scope seam：V2 把上游 implicit Intent generation 留在
协调接口之外，而本实验从 `vague value seed` 开始，包含 seed→task-specific query 的形成。
因此该结果目前只能登记为 `G1_EXTENDED_BOUNDARY_LOCAL_SYNTHETIC`，或在证明这个 seed 已经是
V2 Intent 后降为 `PROJECTION_ONLY`；它不能未经说明就作为 V2 协调接口内的 query-genesis
证据。这是作用域校正，不取消实验在扩展问题上的局部正结果。

## G2 + G5：关系与权威的 crossed square

实验：
[`experiments/wave-009-g2-g5-crossed-square/`](./experiments/wave-009-g2-g5-crossed-square/)

### 结果

- 24 个冻结 synthetic worlds，168 个核心 runs；
- B0 direct center：G2 `24/24`、G5 `24/24`、integration `24/24`；
- B5 existing-component composition：G2 `24/24`、G5 `24/24`、integration `24/24`；
- B1 workflow：G2 `24/24`、G5 `21/24`；三个失败均为 duplicate reservation；
- 28/28 tests 通过；
- 冻结 output SHA-256：
  `7b618c626a7f4d466eeeab295d531a5257776f2f45d1e363ffdbab0587e6d28a`。

这一区分很重要：workflow receipt 不等于原子 reservation；policy Allow 也不等于
Commitment。B5 只有把这些现成能力按边界串联后才完整通过。

### 攻击复核

- 66 个扩展 sequence/missing/duplicate cells 全部拒绝；
- 100 个 fresh single-process broker races 都恰好 `1 success + 1 conflict`；
- cross-world、top-level bytes、old head、old version、event transplant 全部拒绝；
- completed-run operations、任一 ledger 或 exit 被篡改都会使 seal 失效；
- T5 parent-owned state、readback 与 idempotency 通过；
- 11 项 residual matrix 任一行失败都会取消 positive/no-residual。

完整 66-cell 扩展是最终审查运行证据，当前冻结报告内只保存 12 个重点 cells；这是非阻断的
跨会话复现缺口，应在下一次回归包中补存。

### 当前最窄 claim

`POSITIVE_LOCAL_SYNTHETIC_EXISTING_COMPOSITION_SCOPED`：

> 在受信 parent、显式结构化语义、当前 section/event 绑定、严格顺序与数量、单进程原子
> reservation、completed-run seal 和 11 行 residual matrix 下，同一 authoring stream
> 中的 B0 与 B5 都能重建当前 G2/G5 核心真值和 integration readiness。

它不是三个独立成熟产品、自然语言、真实授权、分布式线性一致性、生产或 V1/V2 一般解。

## G3：formation reachability

Wave 008 的 QHM-1 保持已通过的局部结果：10 worlds / 30 runs / 18 qualified /
9 bounded unreachable / 3 open unknown，15 tests 经独立攻击复核。

Wave 009 已冻结 QHM-2 设计，但尚未实现。它把单一 reachability 拆成：

- `R_exists`
- `R_actual`
- `R_effect_robust`
- `R_safe_robust`
- `R_terminal_robust`

并显式区分 fixed hidden policy、declared conditional、Principal deliberative formation、
Principal revision 和 controller substitution。当前最强成熟候选是 contingent planner 或
strong center + distributed Principal holders + purpose-limited consent/contract workflow +
PSI/ZK/TEE/code-to-data + parent verifier。

## G4 + G6 + G7：依赖、Effect 与安全 reopen

T6 已冻结 mutation-replay 设计，没有合格 base-run 和 oracle dependency graph，因此状态仍是：

```text
MUTATION_REPLAY_SPEC / NOT RUN
```

最强成熟组合是：

- current authority head + probe + reservation + attestation/history；
- durable workflow + outbox + idempotency/causal ID + target readback；
- Effect / Adoption / Acceptance / Settlement 分域 receipt；
- dependency-aware migration、recovery 与 reopen。

最强反例是 hidden dependency：两个决策前公开 transcript 完全相同，只在未表达依赖上不同。
这时强中心也不能同时避免 unsafe rely 与 missed reuse。必须新增观察、显式 dependency，或
诚实保持 Unknown。

## 两个 Pro 的独立作用

本轮通过内置浏览器启动了两个分离会话，没有使用 AgentKey；两个会话现在都已完成：

1. 独立问题重建线没有接收本地 Wave 009 返回或实现选择。Pro 独立选择
   `X1 BLIND-JOINT-BID-CROSSOVER` 与 `X2 PROSPECTIVE-EPISODE-CLOSURE`：先在同一 blind
   world family 中保留 G1/G2/G3/G5 truth owners，再把 authority-valid outputs 送入
   G4/G6/G7 prospective closure。
2. 现成方案线被要求优先寻找 mature/central/general-model/composed solution，不预设通爻
   架构。其完成答复提出 `Authority-Gated Joint-Action Case System`：集中规划 +
   local authority evidence，并给出完整性的材料条件。

两条返回都只保存了结构化观察摘要，不是逐字 raw response。独立线的页面报告约 67,459 个
可见字符；现成方案线的完整 Markdown 报告已在页面预览中打开，但三个生成附件没有产生可
取回的本地下载。外部报告只承担竞争解释、先验技术与实验候选生成，不承担本地实验的独立
证明。

见：

- [`external/pro-wave009-independent-001/run.json`](./external/pro-wave009-independent-001/run.json)
- [`external/pro-wave009-independent-001/RESPONSE-SUMMARY.md`](./external/pro-wave009-independent-001/RESPONSE-SUMMARY.md)
- [`external/pro-wave009-existing-solution-001/run.json`](./external/pro-wave009-existing-solution-001/run.json)
- [`external/pro-wave009-existing-solution-001/RESPONSE-SUMMARY.md`](./external/pro-wave009-existing-solution-001/RESPONSE-SUMMARY.md)

## 七线当前状态

| 线 | 本轮状态 | 当前能够说什么 | 不能说什么 |
|---|---|---|---|
| G1 | local synthetic implemented + attacked | 强中心/Router 在当前 query-genesis 矩阵等价且完整 | 真实开放世界发现已解决 |
| G2 | local synthetic implemented + attacked | B0/B5 在当前 relation truth 上 24/24 | 真实关系已共同认领 |
| G3 | QHM-1 complete；QHM-2 design only | bounded formation 与 robust policy 问题已区分 | QHM-2 已运行 |
| G4 | evaluator/spec only | reliance 必须是 attempt 前预测 | 前瞻可靠性已有覆盖率 |
| G5 | local synthetic implemented + attacked | B0/B5 在当前 Authority truth 上 24/24 | 真实 Mandate/Commitment 已发生 |
| G6 | evaluator/spec only | Effect ladder 必须由目标域分别 read back | workflow complete 等于现实效力 |
| G7 | evaluator/spec only | hidden dependency 限制最小 reopen | 生产漂移与恢复已解决 |

## 统一的可迁移原则

> 以 truth owner 为边界进行组合，把每次非蕴含跨越变成显式、版本化、可撤销的证据门。

这不是要求创建新协议。它可以由现有系统、强中心、人工制度、adapter 和少量 glue 完成。
只有在同一任务、同一信息与 Authority 条件下，成熟组合仍无法闭合某个有界跨越时，才建立
新机制候选。

## 下一条最高价值行动

下一轮不再继续平行增加概念，而采用 Pro 独立提出、也能解释本地第二返回的两段式实验：

```text
X1 BLIND-JOINT-BID-CROSSOVER
  G1 Principal-accepted SemanticQuery
  → G2 RelationVersion
  → G3 causal classification
  → G5 Authority + atomic reservation

X2 PROSPECTIVE-EPISODE-CLOSURE
  X1 authority-valid output
  → G4 attempt-before-reliance prediction
  → G5 execution-time gate
  → G6 target-domain Effect ladder readback
  → G7 dependency-aware continue/reopen
```

所有方法在同一 frozen task、信息、budget、Authority 与 truth-owner 条件下运行：

- optimized strong center；
- existing-component composition；
- platform direct；
- general-model policy；
- 只有真实残余出现时才加入新构造。

Pro 建议 X1 66 worlds、X2 72 worlds；后续独立审计已**拒绝把这两个数字作为评分分母**：
motif 尚未逐项冻结，identifier/order permutation 只是 metamorphic replay，T5 必须单列，
而 X2 population 还取决于 X1 实际 outputs。数字只保留为未审计运行预算草案。两段式设计的
目的不是制造“大一统对象”，而是检验本轮识别的跨合同证据门是否足以让现成组件真正首尾
闭合。它为 T6 创建合格 base trace，也给 QHM-2 的 actual-policy 分支留下接口，信息增益
高于继续在单线内扩充同质实验。

本文件不激活 Problem、不晋升 MechanismProfile、不改变 NAC 七档案或任何稳定主张。
