---
derived_view: true
source_path: Towow_Complete_Research_Archive_v1.2_2026-07-27/02_WORKSPACE_SNAPSHOT/Towow_R8_OPC_Constructive_Closure_v1.1/paper/通爻_主权智能主体共同现实形成_正式论文_v1.1.md
source_sha256: 42b3c6fa1da3a56ce07a20be6283d1efcfa4b15e9069b84d0634934067f86b6c
source_line_start: 654
source_line_end: 795
source_heading: "7　从搜索到行动构成：Coordination Schema、SJAC 与 JAA"
---

> 本文件是导航用派生视图。原始文本未改动；引用研究证据时应回到上列源文件与行号。

# 7　从搜索到行动构成：Coordination Schema、SJAC 与 JAA

## 7.1 搜索范式的四个隐含假设

一个标准搜索或匹配问题通常预设：

1. 查询已经存在；
2. 候选集合或生成空间已经定义；
3. 相关性或效用函数可以计算；
4. 返回结果的行动含义已经知道。

开放主体协调会同时破坏这些假设。某个 OPC 可能只知道“我想扩大交付能力，但不愿雇全职员工”，并不知道需要的是联合投标、可撤销数据合作、临时项目团队还是标准 SaaS；潜在伙伴也可能没有公开对应能力，因为该能力只有在特定预算、工具、时间和授权组合下才会出现。

因此，搜索不是无用，而是构成完成后的子程序。系统必须先形成“什么值得搜索”和“什么结果可以进入现实”的语法。

## 7.2 高阶互补与超边

成对匹配无法完整表达三方及以上互补。例如：

- A 有客户需求但无技术；
- B 有技术但无行业数据授权；
- C 有数据授权但只有在 A 提供最低订单、B 接受本地执行时才愿意加入。

任意两方单独都不可行，三方组合才产生联合能力。若平台只对 pairwise score 排序，所有边权都可能为零，从而永远发现不了三元超边。这个反例表明，开放协调需要允许 `COLUMN` 响应和临时联盟构成，而不能只用静态主体配对。

## 7.3 Coordination Schema

**定义 10（Coordination Schema）。** 对某一关系族，协调模式写为：

\[
\Gamma = \langle R,V,T,A,E,D,O \rangle,
\]

其中：

- \(R\)：参与者、角色、代表和职责拓扑；
- \(V\)：对象、动作、主张和条件词汇；
- \(T\)：状态转移、恢复、退出、争议和补偿；
- \(A\)：提出、认领、授权、承诺、执行、见证、采用和接受权；
- \(E\)：证据类型、来源、见证和保证门；
- \(D\)：披露、用途、派生、保留、训练和再传递权；
- \(O\)：Commit、Reject、Conditional、Unknown、Effect、Adoption、Acceptance 和 Settlement 的成立语义。

价格、日期、数量等具体值属于 Relation 实例 \(x\)，不必每次都改变 \(\Gamma\)。但若价格跨过董事会审批阈值，导致新增必要 Authority Locus，则该变化从参数变化转为 material schema change。

## 7.4 Institutional Frame 与 Relation-specific Version

复杂社会行动通常不从零开始。法律、行业、平台和组织已提供部分规则。本文区分：

\[
\Gamma^I \quad \text{Institutional Frame},
\]

\[
\Gamma^R_v \quad \text{relation-specific version } v.
\]

二者使用同一七维结构，RelationVersion 通过 `inherits_from` 和 `overrides` 继承或覆盖制度框架。成熟并购可在既有公司法、合同和监管程序内处理大量复杂参数；此时问题复杂，却未必需要开放构成。相反，一个看似简单的数据合作若其数据位置、训练权、派生权和业务接受尚未定义，就可能需要打开 \(\Gamma^R\) 甚至修订 \(\Gamma^I\)。

## 7.5 Material change

**定义 11（物质性变化）。** 对当前任务状态 \(s\) 和 Relation Schema \(\Gamma\)，变化 \(\Delta\Gamma\) 若改变以下任一项，则为 material：

- 当前可达动作集合；
- 必要参与者或 Authority Locus；
- Effect 的见证和成立条件；
- 数据或派生权；
- Acceptance、退出、恢复和补偿路径；
- 某主体当前已认领承诺的风险或责任范围。

形式地，若

\[
Reach(s,\Gamma) \neq Reach(s,\Gamma+\Delta\Gamma)
\]

或存在主体 \(i\) 使其规范义务集合

\[
Obl_i(s,\Gamma) \neq Obl_i(s,\Gamma+\Delta\Gamma),
\]

则变化为 material。显示名称、不可达归档动作或不影响当前任务的扩展可以是 non-material。

## 7.6 SJAC：主权联合行动构成

SJAC 不是新的协议 root，而是对 L2–L5 过程的理论名称。它回答：多个主体如何在不交出完整世界的情况下，共同形成一个可被各自本地 Oracle 解释和约束的联合行动结构。

SJAC 至少包含：

1. 当前问题和目标版本；
2. 参与主体、角色与 Standing；
3. 未知项和竞争解释；
4. 候选动作与组合结构；
5. 本地边界和 countercondition；
6. 能力与证据要求；
7. 权威、认领和承诺；
8. Effect、Adoption、Acceptance 与 reopen。

它不是“所有人达成同一世界观”，而是形成一个最小的、可执行的跨世界接口。

## 7.7 JAA：版本化共同协调介质

**定义 12（JAA）。** Joint Action Artifact 是一个版本化、可引用、可局部认领的共同协调介质，包含当前 RelationVersion、未决项、候选、证据、Stance、依赖和历史，但自身不成为所有事实的权威来源。

JAA 的关键性质：

- **多视图**：每个主体可以保留本地解释，同时引用共同版本；
- **精确版本认领**：Recognition 和 Commitment 必须指向具体哈希或版本；
- **草稿与承诺分离**：草稿可协同编辑，承诺不能因自动合并而改变；
- **来源保留**：每项主张指向本地 Authority 或 Evidence；
- **差异摘要**：material change 必须向受影响主体解释；
- **局部可见**：主体不必看到所有私有证据，只需看到自己认领所需的充分证明。

JAA 因而更像可编译的共同工作对象，而非中心数据库里的“真相记录”。

## 7.8 三个嵌套循环

联合行动构成不是一次协商，而是三个耦合循环：

### 语义构成循环

形成问题、角色、动作词汇、条件和结果语义。输出是新的或修订的 \(\Gamma^R\)。

### 可行域发现循环

通过本地 Oracle、probe、切割、见证和新列，发现当前候选在哪些条件下可行。输出是合格候选、Defeater 或新形成动作。

### 规范闭合循环

相关 Authority Locus 对精确版本作出 Recognition、Delegation、Commitment、Reject 或 Conditional；资源被预留，退出和接受被明确。

三个循环相互回馈：规范拒绝可暴露语义缺口；可行域反例可要求新角色；语义修订会使已有承诺失效。

![协调构成的三个嵌套循环：语义、可行域与规范闭合。](../figures/coordination_constitution_loops.png){width=88%}

## 7.9 过程完备而非检索完备

开放世界无法保证枚举所有潜在主体和行动。本文因此不追求“检索完备”，而追求**过程完备性**：对于当前任务中出现的每个重要 Unknown，系统至少能够把它分类为可询问、可验证、可试验、可授权、可重构、可拒绝或不可判断，并保存其来源与后续路径。

过程完备性不保证找到全局最优合作，但能防止系统把未探索的可能性误写成不存在，把主体拒绝误写成技术失败，或把模型猜想误写成共同事实。

