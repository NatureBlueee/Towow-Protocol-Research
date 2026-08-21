# Wave010 G1 独立母线综合

## 总结论

当前没有证据表明 G1 存在必须新发明机制才能填补的技术 residual。

更准确的判断是：

- 最佳现成解是“权威感知强中心或成熟组合，调用端侧事件、最小投影、current-head 目录、隐私匹配、local oracle 与互惠 probe”。强中心合法获得相同信息时，完全可以胜出。
- 真正不可消除的是合法观测不足：若机会存在与不存在的两个世界产生完全相同的合法 transcript，任何模型、中心或协议都不能区分。正确结果是 `Unknown/Reject/Defer`，不是制造发现。
- 尚未完成的是一个新的、盲化、方法中立的 T1→T2/T4 同分母实验。Wave010 X1 仍是设计候选，没有 runner、scoreable population 或 coverage。[Wave010 状态](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/WAVE-010-X1-DESIGN-CANDIDATE.md:4)

G1 在 V2 内应精确定义为：

> 给定一个已经进入协调接口、字段和规范地位可能仍为 Unknown 的 Intent，在动态、局部私有、允许拒绝的世界中，发现尚未成为 card、catalog item 或共同对象的互补方、能力、约束和既存路径，并形成当前、最小披露、可追溯的 `CANDIDATE_NOT_COMMITMENT`；不能发现时诚实保留边界。

上游 event/vague seed → Intent generation 不计入 V1/V2 G1；V2 已明确将其排除。[V2 边界](/Users/nature/通爻协议研究/research/projects/joint-action-formation/problem/v2.md:54) [Correction 002](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/TASK-TRUTH-CORRECTION-002.md:45)

## Supported / Failed / Unknown

### Supported

- Wave002 的早期盲跑证明目录与本地投影具有真实互补性：目录 `0/8`、本地投影 `1/8`、两者组合 `5/8`；组合仍缺方向判断、合法 reciprocal probe 和关系 handoff。[实际结果](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/WAVE-002-FIRST-BLIND-RUNS.md:14)
- Wave009 确实运行了一个固定词汇、有限 provider 菜单下的路由实验。其报告中目录、本地投影、privacy predicate、reciprocal probe 分别命中 `3/10、3/10、1/10、1/10`；强中心和 Router 均为 `10/10`，且行为、账面成本和披露相同。
- 这个 `10/10` 支持“在 query 已足够结构化、合法 local oracle 可读时，强中心可以完成当前有限路由”，不支持强中心必须被替代。
- 零披露、完整召回、零误唤醒三者不能在合法 transcript 不可区分时同时满足。新增合法观察会推翻“不可区分”的前提，但不会推翻该判别边界。

### Failed

主线程代码复核进一步收窄了 Wave009，不能继续把它称为广义 query genesis 或完整 G1：

- 唯一 Intent 被固定为 translation 任务及 `purpose/direction/constraints/version`；策略逐项索取这些字段后组装 exact query。[固定语义](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-009-g1-query-genesis/query_genesis/worlds.py:146) [固定 facet 流程](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-009-g1-query-genesis/query_genesis/strategies.py:22)
- evaluator 又从同一个 hidden Intent 构造 exact query，并只遍历作者预置的 index/local/private/probe 菜单；因此它证明固定 action grammar 内的路由，不证明未预见语义维度的发现。[evaluator 构造](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-009-g1-query-genesis/query_genesis/evaluator.py:58)
- `N`、`P` 配对同时改变了局部事实和 clarification policy，不是单一变量对照；`Z` 配对在 requester 澄清阶段就被零披露截断，没有检验 query 已形成后的 provider 侧不可区分。[world 定义](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-009-g1-query-genesis/query_genesis/worlds.py:275)
- `D_actual` 与 handoff 可达性被定义为同一个 `HANDOFF in visited`，无法表达“及时发现、但 handoff 前撤销”。[truth 计算](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-009-g1-query-genesis/query_genesis/evaluator.py:164)
- disclosure 的 `violation` 由 runtime 直接写成 `False`；因此报告的 `robust_safety=1.0` 不能证明真实 policy 合规或拒绝后无旁路。[披露记录](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-009-g1-query-genesis/query_genesis/evidence.py:272)

所以：实际运行行为有效，但“动态未声明维度发现、隐私安全、完整 G1”这些更强解释失败。

### Unknown

- 强中心、成熟组合、人类 broker 谁能在新的 T1/T2/T4 盲任务上完整胜出。
- 真实 ARD、Agent Card registry、RAG、PSI/MPC/TEE 产品在本任务分母上的表现。
- 真实拒绝率、累计披露、规模、延迟、维护和生命周期净值。
- 是否存在经过公平同臂比较后仍需要新机制的残余。
- T1 发现能力能否迁移到 T2/T4，而不丢失 Principal、Authority、version 与 refusal。

## 实际任务矩阵

| 任务 | 已有实际证据 | G1 有效解决程度 | 仍缺什么 |
|---|---|---|---|
| T1 动态未声明发现 | Wave002：目录 `0/8`、本地投影 `1/8`、组合 `5/8`；Wave009 报告固定词汇下中心/Router `10/10` | 目录与端侧投影互补已支持；固定 schema 路由可解 | 未预枚举维度、正交 paired worlds、真实 policy violation、分时 discovery/handoff、独立 holdout |
| T2 企业只读试点 | blind candidate 把拒绝推进为合法 probe 候选；五分支 probe simulator 已运行 | 合法下一步和状态不偷渡得到支持；不是 G1 独立评分 | 原始案例答案已公开；没有 fresh G1 evaluator，也没有强中心/成熟组合的完整同臂复用 |
| T4 联合投标 | 旧 baseline `0.60/PARTIAL`，但预写了角色身份；Wave010 新 X1 未运行 | 私有 column/probe 有局部证据；未证明冷启动 filler discovery | fresh role fillers、开放语义、强中心/组合/人类公平比较、撤销前后 handoff、迁移 |

因此不能把 T2 的 `8/8` 或 T4 的 `0.60` 当成 G1 coverage；它们评价的是其他责任链或旧任务结构。

## 最佳现有组合

```text
IntentAtCoordinationInterface
→ Principal clarification / 端侧 material-event trigger
→ purpose-bound 最小投影
→ current-head ARD/catalog/Agent Card + RAG（仅已表达材料）
→ 若已有 shared predicate：PSI/MPC/TEE/code-to-data
→ coarse candidate：receipt-backed reciprocal probe / local oracle
→ handoff 前重新读取 policy、version、revocation head
→ CANDIDATE_NOT_COMMITMENT 或精确 Unknown/Refusal/Defer
→ 交给 G2；不在 G1 偷渡 Relation、Mandate、Commitment 或 capability
```

强中心可以编排整个组合，但不能成为各 Principal 的 truth owner。只要 raw centralization 合法，或各 owner 提供 purpose-bound local oracle，强中心可能是最简单的完整答案。若事实不能集中，仍可让中心只编排端侧接口。

人工 broker 应作为公平强基线：它可能通过隐性知识形成新问题和语义，但要计入会议、等待、不可复现、治理与知识迁移成本。

## 为什么业内已有这些技术却仍可能没解决

仓库证据不能证明“业内没有解决”；只能证明“组件存在不自动等于完整任务闭合”。

主要断点是：

- RAG/目录要求内容和 query 已表达；
- card 命中不蕴含 SEEK/OFFER 互补；
- privacy match 要求 shared predicate 已形成；
- local trigger 不蕴含 Principal 愿意披露；
- probe compatibility 不蕴含关系、能力或承诺；
- static index 不蕴含 current head；
- owner refusal、offline、open-world silence 与不存在不同；
- 一个组件的输出若没有 current、scope-bound、可撤销的 owner receipt，就不能安全成为下一组件的输入；
- 组合的披露、接入、等待、治理和维护成本可能吞噬发现价值。

如果成熟组合把这些跨合同门都闭合，它就是通爻的成功方案，不再需要新增机制。

## 真实 residual

1. **原则性边界，而非技术缺口**：合法 transcript 相同的两个世界不可区分。只能新增合法 observation、改变环境或保持 Unknown。
2. **实验 residual**：尚无 fresh、盲化、同 `BE0` 的强中心/成熟组合/人类跨 T1/T2/T4 比较。
3. **当前仪器 residual**：Wave009 固定词汇、非正交 pair、`D_actual=H`、自报式 privacy safety，不能回答广义 G1。
4. **没有被证明的 residual**：不存在证据支持“还缺一个通爻专有 discovery protocol”。

## 下一项可执行模拟

建议冻结 `G1-SEAM-CROSSOVER-v0`；第一可运行 slice 是 `T1-MN-01`，随后用 fresh T2/T4 skin 做迁移。

### 冻结对象

`S0、V0、BE0、Q_episode、IntentAtCoordinationInterface、policy、population head、time-indexed events、D_discovery(t)、H_handoff(t)、semantic equivalence classes、budget/horizon`。

必须将 `D_discovery` 与 `H_handoff` 分开：发现后撤销可记为“发现成功、handoff 正确阻断”。

### 首轮 paired worlds

- local fact exists/absent，双方 clarification policy 完全相同；
- query 已形成后，provider 侧 zero-disclosure exists/absent，合法 transcript 完全相同；
- current head 分别在 search 后、qualification 后、handoff 前撤销；
- SEEK/OFFER 与同 facet SEEK/SEEK decoy；
- `OFFLINE / SIGNED_REFUSAL / UNEXPRESSED / CLOSED-ABSENT`；
- irrelevant event false wakeup；
- open-population silence 与有 membership-root 的 bounded absence；
- 一个相关维度不在初始目录/schema 中，但可由 generic local projection 提出。

每个 pair 只改变一个 owner-owned fragment；若差异会传播到其他线，G1 在 terminal handoff 截断，或显式 mask，不再伪称其他 truth 相同。

### 公平 arms

- `DIRECTORY/CARD/RAG`
- `LOCAL-PROJECTION`
- `LOCAL-PRIVACY/PROBE`
- `AUTHORITY-AWARE-STRONG-CENTER`
- `MATURE-COMPOSITION`
- `EXPERT-HUMAN-BROKER`
- 任意 candidate；没有 residual 时可以等同于成熟组合

全部使用相同模型、generic API、询问轮数、local oracle、披露预算、Authority envelope、时限和恢复能力。

### 方法中立 API

`observe_public_state / ask(owner, free_form_claim, disclosure_envelope) / submit_projection / search / propose_private_test / probe / read_current_head / submit_handoff / stop`。

不暴露合法 request 菜单，不强迫成熟方案原生生成 G1/G2/G3/G5 对象；arm-specific adapter 可以把原生结果转成共同输出。

### 评分和 hard gates

测量：

- `D_discovery` recall 与 `H_handoff` precision；
- structural miss、false wakeup；
- typed-state confusion；
- discovery latency 与 revoke-to-block latency；
- 多轮、多接收方累计 disclosure/inference leakage；
- refusal 后重复询问和跨 recipient 旁路；
- stale handoff；
- 模型、endpoint、人工、治理、恢复成本。

任一以下失败即不得称 scoped solution：

- oracle/branch leakage；
- indistinguishable pair 输出不同；
- open-world false `ABSENT`；
- 拒绝后旁路；
- 未授权 disclosure；
- stale/revoked handoff；
- discovery candidate 偷渡 capability/Mandate/Commitment；
- 全部停止而未达到 positive liveness floor；
- baseline access 或预算不等。

T2 迁移必须使用全新 skin，不复用当前答案形 request 菜单；T4 必须隐藏可替换 filler 身份，并允许多组等义 consortium。实际 finalized episodes 才进入分母，不能预先把设计数量写成 coverage。

## 会推翻本结论的反例

- fresh、隔离的 T1/T2/T4 中，强中心或成熟组合在无预制 query/card、同等 access 下通过全部 recall、privacy、refusal、drift 和 false-wakeup gate：这会关闭新增机制必要性，是最希望看到的成功。
- 现实制度保证所有承重变量在 Intent 接口前已经 current、完整且强制声明：G1 可退化为 catalog/center routing。
- 找到此前遗漏且政策允许的 observation，使 zero-disclosure pair 可区分：需要重开 world，不是算法违反不可区分定理。
- 隐私计算能在没有预共享 predicate 时，以不增加泄露、保留拒绝的方式形成新 predicate，并在 holdout 中复现。
- 人工 broker 在相同任务上完整、可迁移且生命周期成本更低：应直接采用制度解。
- 一个更小的 non-success 状态集合在所有 refusal、retry、retention 与 handoff mutation 上行为无损：应删除多余状态。

## 证据边界

本轮只读，未修改文件、未运行生产或新模拟。三条子研究线均已返回，主线程另外逐行检查了 Wave009 实现。现有数字均来自本地合成、同一研究环境，不是产品、真人、生产或跨行业证据。

按 `sol-pro-research-loop` 的最小披露与本地复核原则，本轮没有再次调用外部 Pro、没有联网，也没有发送或引用 NAC 专利交底、凭据、个人数据或无关历史。当前工作区有既有未提交改动，本轮未触碰。

