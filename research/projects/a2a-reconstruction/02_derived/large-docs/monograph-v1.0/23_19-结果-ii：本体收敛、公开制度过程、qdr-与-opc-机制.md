---
derived_view: true
source_path: Towow_Complete_Research_Archive_v1.2_2026-07-27/02_WORKSPACE_SNAPSHOT/Towow_Unified_Paper_v1.0_formal/通爻_主权智能主体共同现实形成_正式论文_v1.0.md
source_sha256: 7f92cd950ddb796f193509529268f22b12ab1de3a6139ee71ffa13d0ecc1a65e
source_line_start: 2368
source_line_end: 2603
source_heading: "19　结果 II：本体收敛、公开制度过程、QDR 与 OPC 机制"
---

> 本文件是导航用派生视图。原始文本未改动；引用研究证据时应回到上列源文件与行号。

# 19　结果 II：本体收敛、公开制度过程、QDR 与 OPC 机制

## 19.1 v0.4 本体收敛：重要差异不等于都需要顶层对象

在 50,000 个生成场景、250,000 次查询中，使用 `Mandate + typed Event + provenance edge + conditional Commitment` 的收敛表示在生成器查询集上错误为 0；naive flatten 产生 48,926 次错误，错误率 19.5704%。24.624% 的场景中，联合制品权利因为需要独立认领、修改或执行，必须提升为独立 Commitment。

该实验区分三种常见误区：

- 把所有差异压成布尔字段，会丢失版本、撤销和来源；
- 把所有差异都做成顶层 root，会增加协议和一致性负担；
- 正确的物化级别取决于独立权威和生命周期需求。

实验没有证明六 root 是唯一最优本体，也没有证明现实法律制度一定接受这种映射。

**Design Delta：**

| 历史概念 | 默认表示 | 升级条件 |
|---|---|---|
| UsageGrant | Mandate 的用途/数据 scope | 独立签发、跨关系引用、撤销 |
| DataUseEvent | typed Event | 通常不升级 |
| DerivationRecord | provenance edge | 谱系本身需独立治理/争议 |
| JointArtifactRights | policy/conditional Commitment | 多方独立认领、修改、执行、救济 |
| LearningUpdate | Effect event | 跨任务持久状态、监管、撤销义务 |

## 19.2 Relation Schema materiality：任何变化都重开和永不重开都失败

30,000 个有界变化的结果：

- never reopen 错误率 55.26%；
- always reopen 错误率 44.74%；
- any schema diff 错误率 26.76%；
- typed materiality checker 在生成器定义内错误率 0。

该结果支持用可达轨迹、角色、Authority、Effect、Data 和 Outcome 语义判断 materiality，而不是根据“文档是否改变”。但零错误只是因为 ground truth 与 checker 共享形式定义，不证明现实规范争议可以被算法自动解决。

**Design Delta：**

- materiality checker 输出 `MATERIAL / NON_MATERIAL / AMBIGUOUS`；
- `AMBIGUOUS` 升级到相称 Authority，而非模型自决；
- 重开依赖闭包而非全部关系；
- 价格等参数跨越 Authority 阈值时升级为 Schema change；
- 运行时监控用于捕获未建模依赖。

## 19.3 Fieldkit：从聊天纪要到可重算研究对象

v0.4 Fieldkit 通过 11 项测试，虚构样例产生 21 个哈希链事件和 2 个 RelationVersion；v0.5 加入 Standing、jurisdiction、challenge 和 scoped Settlement 后通过 15 项测试；v0.7 扩展至 31 项测试，增加 OPC Operating Envelope、Coordination Context、八机制 Router、五维 Stability、Mandate 撤销、精确 Stance、附件证据和依赖闭包 reopen。

Fieldkit 的证据含义是：真实实验所需的前态、Mandate、RelationVersion、Effect、Acceptance 和 follow-up 可以被结构化记录和独立重算。它不证明用户愿意使用，也不具备生产加密、身份、密钥托管、支付或法律签署。

**Design Delta：**

- 研究材料分为 `private/` 与可共享导出；
- 每次 material change 自动生成差异报告；
- compile readiness 可独立重算；
- 现实实验不再依赖研究者事后写摘要；
- 所有事件引用 exact version 和 Authority Locus。

## 19.4 公开制度档案：真实关系变化多为转化和保护性收缩

PEA-10 选择 10 个公开正式过程案例。主要编码为：1 个 Expansion、3 个 Transformation、5 个 Protective Contraction、1 个 Clarification。外部 Authority 改变路径 7/10，challenge/reopen 出现 6/10。

这说明“形成”不等于扩大交易。真实制度过程常通过附加限制、终止、分拆、监督和救济使关系变得更真实。一个系统若只把新机会和成交视为价值，会错过保护性收缩和快速不成交。

但这些是有意选择的理论样本，不能报告为总体频率；它们也没有 Agent treatment，不能证明通爻造成了任何结果。

## 19.5 三案过程编码与公告消融

Microsoft–LinkedIn、Amazon–iRobot 与 NASA HLS 三案共编码 33 个事件，其中 28/33 达到操作完整。只使用压缩公告时：

- 严格事件召回 18.2%；
- 部分计权召回 25.8%；
- 关键转折加权召回 25.0%；
- Authority Locus 召回约 36.7%。

最终公告能够说明交易完成、终止或项目继续，却大量丢失候选、拒绝、外部权威、证据纳入、版本变化和 contingency。NASA HLS 提供了重要负控制：重大事件发生并不必然要求重构 Schema，若 contingency 已被制度框架预留，变化可以在原机制内吸收。

**Design Delta：**

- 增加 `frame_scope / inherits_from / overrides`；
- 区分 evidence admissibility 与 evidence existence；
- 预留 contingency 作为不重开的正当理由；
- 公开摘要只用于结果视图，不作为过程事实源。

## 19.6 七案扩展：Standing、Declared/Enacted 与多维稳定

扩展数据集包括 Microsoft–LinkedIn、Amazon–iRobot、NASA HLS、Sidewalk Toronto、UK Open Banking、Crossrail 和 California SGMA，共 58 个事件：

- 37 个 material change；
- 51 个关键转折；
- 53/58 在公开资料下达到操作完整，比例 91.4%；
- 58/58 可映射到 \(\Gamma=\langle R,V,T,A,E,D,O\rangle\)；
- 6 个 Standing 实质影响关系；
- 3 个 declared/enacted schema 断裂；
- 18 个部分稳定、部分失稳事件；
- 2 个 reserved contingency 负控制。

“58/58 可映射”不证明七维完备，只说明在当前编码分辨率下没有结构残差；单编码者也可能把无法表达的内容强行解释进既有类别。

### Sidewalk Toronto：Standing 不等于签署权

公开咨询中的公众没有最终合同签字权，但其关于公共控制、数据治理、范围和退出的挑战改变了合法 RelationVersion。系统因此必须允许 affected-party standing，而不能把所有参与者伪装成共同决策人，也不能只记录最后签字者。

### UK Open Banking：技术采用成功不等于治理稳定

正式命令、技术标准和实施实体已经存在，技术交付与采用可以推进；但后续复盘指出决策、资金与治理权限并未由技术实施组充分承载，缺少阶段性治理复核。由此导出：

\[
RuleDeclared \neq RuleEnacted.
\]

一条规则的存在还需要观察、信息到达、干预权、资源和制裁/升级路径，才能成为运行中的制度。

### Crossrail：局部包件完成不等于端到端 Effect

大量合同和局部工程结果并不自动构成可运营铁路。接口、依赖和整体时序未被统一观察时，局部 Effect 无法推出端到端 Effect。这一案例强化了目标世界 witness 与跨组件依赖图。

### SGMA：同一公共目标不产生唯一协调机制

州级法律要求地方机构协调，但允许多种组织形式。不同流域采用 MOU、联合机构、共享数据、中心协调和本地自治的不同组合。不可折叠权威不推出统一去中心化结构。

**Design Delta：**

- Relation Schema 区分 \(\Gamma^I\) 与 \(\Gamma^R\)；
- Standing 进入 R/A 属性与 Gate；
- 增加 Enactment Assurance；
- 稳定由五维向量表示；
- Compile 被理解为制度化，而不只是代码生成；
- Router 选择多中心、中心、人类和 Agent 的组合。

## 19.7 QDR：类似顾虑并不唯一决定协调配置

QDR 数据处理结果：

- 52 份去标识化访谈；
- 3 份工作簿；
- 381,329 个受访者词；
- 4,394 个唯一检索单元；
- 6,677 个跨代码命中；
- 18 个可匹配流域。

18 个流域出现 15 种协调配置。按最相近协调顾虑寻找 nearest neighbor，仅 1/18 复现相同配置。该结果反驳简单规则：“面对相似问题，应选择同一种协调机制”。机制选择依赖权威拓扑、自治、资源、制度历史、目标结果与可执行结构的组合。

![QDR 协调配置压力测试：多数流域配置独特，最相近顾虑只在 1/18 中复现相同配置。](figures/fig05_qdr_configurations.png){width=74%}

自动检索的 54 项单分析者审计中：

- 42 项有效；
- 7 项部分有效；
- 5 项假阳性；
- 严格有效率 77.8%；
- 有效或部分有效为 90.7%。

这说明自动检索适合作为候选生成器，不适合直接报告主题 prevalence。QDR 不是 OPC 数据，其正确用途是机制与本体校准：真实访谈中确实能观察到自治、权威、代表、资源和机制选择，但不能用其频率预测超级个体。

## 19.8 盲化历史诊断：高召回，不是预言器

11 个时间截点的平均 F1：

| 方法 | F1 |
|---|---:|
| No change | 0.000 |
| Prior mode | 0.516 |
| Last event | 0.677 |
| Authority-aware | 0.756 |

Authority-aware 召回达到 0.891，但完整维度集合 exact match 为 0/11。

![时间截断结构诊断结果。](figures/fig06_blind_f1.png){width=74%}

结果支持把结构诊断器用于高召回风险扫描和 probe 排序，不支持让它自动预测、拒绝或重开。零 exact match 表明真实变化通常同时包含未被当前摘要充分捕捉的维度。

**Design Delta：**

```text
结构诊断
→ 候选缺口排序
→ probe 成本与风险估计
→ 选择最小可判别问题
→ 返回相称 Authority Locus
```

而不是“模型预测将变化，所以自动修改关系”。

## 19.9 三机制 Replay：100% 是编码保真，不是系统效果

对 58 事件的结构查询召回：

- 压缩公告：10.2%；
- 单一全局状态：7.0%；
- Authority-aware 版本图：100%。

版本图使用与人工事件相同的 Authority、版本和依赖 Schema，因此 100% 证明已编码信息能够被无损保存。它不证明自然语言自动抽取准确，也不证明用户体验、商业结果或决策质量。

该实验仍有建设性价值：它确认压缩公告和覆盖式单状态不适合作为审计事实内核。若单状态加入全部历史、来源和依赖，它实际上会演化为等价版本图。

## 19.10 OPC 24 场景：最终满分不如初始失败重要

构造场景结果：

| 机制 | 结构有效案例 |
|---|---:|
| 固定平台 | 6/24 |
| 单一全局 Agent | 0/24 |
| 修复后组合 Router | 24/24 |

![OPC 构造场景中的结构有效性。24/24 是修复后的构造一致性，不是现实成功率。](figures/fig07_opc_validity.png){width=74%}

24/24 不能写成“通爻完胜”，因为场景和 Router 来自同一理论。真正信息增量来自初始 Router 的五类失败：

1. 多方排期只调用中心优化器，没有真实资源预留；
2. 争议流程没有冻结不可逆动作、保存旧版本和分离 Effect/Acceptance；
3. OPC 内部自执行没有版本化 Operation Specification；
4. 标准化但不可逆工作缺 pre-effect validation；
5. 候选计算集中后错误合并了多个本地 Authority Gate。

修复这些失败后，Router 才在构造定义下通过。

**Design Delta：**

- 机制图增加 resource reservation 节点；
- 争议路由强制 freeze、preserve、remedy 和 human adjudication；
- SELF_EXECUTION 仍需 Mandate 和 Operation；
- 不可逆确定性服务增加 pre-effect Gate；
- 中心计算与本地 Authority Gate 正交。

## 19.11 结果的总体限制

v0.4–v0.7 的证据使理论更可操作，也暴露了其容易自证的风险。生成器、Schema 和 Router 均由研究者构造；公开过程由既有理论编码；QDR 不是 OPC；版本图使用同构查询。因此，这些结果最适合支持：

- 概念和状态能否被清楚区分；
- 某种简化在已知查询上会丢失什么；
- 哪些设计缺口必须在进入真人实验前修复；
- 真实制度中是否存在对应现象。

它们不能替代：真实委托、解释理解、相对强基线、长期使用和净价值。

