---
derived_view: true
source_path: Towow_Complete_Research_Archive_v1.2_2026-07-27/02_WORKSPACE_SNAPSHOT/Towow_R8_OPC_Constructive_Closure_v1.1/paper/通爻_主权智能主体共同现实形成_正式论文_v1.1.md
source_sha256: 42b3c6fa1da3a56ce07a20be6283d1efcfa4b15e9069b84d0634934067f86b6c
source_line_start: 127
source_line_end: 212
source_heading: "2　研究方法：以主张—证据—Design Delta 组织累积研究"
---

> 本文件是导航用派生视图。原始文本未改动；引用研究证据时应回到上列源文件与行号。

# 2　研究方法：以主张—证据—Design Delta 组织累积研究

## 2.1 为什么不能按“第一轮、第二轮、第三轮”写论文

本研究经历了协议设计、语义坐标、边界预言机、生成式协调、能力保障、Harness、现实效力审计、真实模型谈判、跨技术域形成、公开制度过程、QDR 访谈重分析和 OPC 机制构造等多轮工作。若按时间顺序汇编，读者会看到许多术语，却难以判断它们解决的是同一问题的不同层，还是彼此竞争的理论。更严重的是，后续证据经常限定早期主张：NAC 的发现接口仍有价值，但不能承担普遍语义本体；R5.4 证明多轮模型协商能生成丰富条件，却不能证明能力形成；R5C 证明技术域路径可被构造，却不能替代真实 Principal 认领。

因此，本文以**问题依赖**而非历史阶段组织材料，并为每项主张维护五元组：

\[
\mathcal{C} = \langle statement, scope, evidence, alternatives, design\ delta \rangle.
\]

其中 `statement` 是可检验陈述，`scope` 指适用域，`evidence` 指当前最高证据等级，`alternatives` 是尚未排除的竞争解释，`design delta` 是该证据实际改变的系统结构。没有 Design Delta 的实验可以增加形式完整度，却不应自动升级为核心科学贡献。

## 2.2 证据等级

本文采用 E0–E7 的证据阶梯：

| 等级 | 类型 | 能够承担的主张 | 不能承担的主张 |
|---|---|---|---|
| E0 | 概念与定义 | 术语一致性、对象边界 | 现实有效性 |
| E1 | 形式推导、反例、模型检查 | 在假设内的不可能性、保持性质 | 现实频率、用户价值 |
| E2 | 合成机制实验 | 机制能否区分、参数敏感性 | 现实分布、社会接受 |
| E3 | 参考实现与状态机验证 | 可实现性、接口一致性、已建模不变量 | 生产安全、商业价值 |
| E4 | 真实仓库与历史轨迹 | 真实系统中的失败模式和修复 | 人类委托、一般化收益 |
| E5 | 跨技术权威域闭环 | 多域 Effect、Adoption、revoke、recovery | 真实 Principal 认领 |
| E6 | 真实模型 Agent 互动 | 模型协商行为、语言形成能力 | 主体授权与净价值 |
| E7 | 真实 Principal 与生产结果 | 认领、委托、接受、长期价值 | 超出样本和场景的普遍规律 |

该阶梯不是把形式证据排在现实证据“下方”，而是防止不同证据类型互相冒领。一个严格定理可能比小样本用户实验更可靠地证明某个不可能性；但它不能回答用户是否愿意接受系统。一段真实运行轨迹可以证明某个 Effect 的确发生，却不能证明机制在所有情形下更优。

![证据阶梯与每级可承担的主张。越靠上越接近真实 Principal，但并不替代下层形式与工程证据。](../figures/fig7_evidence_ladder.png){width=82%}

## 2.3 资料与分析单元

本文使用六类资料：

1. **理论与协议档案**：原始通爻协议、HDC/FHRR/NAC、四动词、BIC、SJAC、JAA、PFE、CRA、Harness 和 Compiled World；
2. **合成与形式实验**：边界披露、团队构成、概率门、并发预留、本体收敛、Schema materiality 等；
3. **真实工程材料**：仓库、日志、状态机、Effect readback、能力资格化与 reference engine；
4. **真实模型互动**：R5.4 多轮协商负对照；
5. **跨技术权威域实验**：R5C 的 adoption、revocation、offline/unknown、recovery 和独立 readback；
6. **公开制度与访谈材料**：并购、监管、基础设施、开放银行、城市治理、地下水协调及 52 份去标识化访谈。

分析单元不是“文档”，而是主张、事件、RelationVersion、Authority Locus、Effect、Acceptance 和 Design Delta。公开案例中的事实由正式来源支持，但对其进行 Relation Schema 编码仍属于本文分析，不应与原始事实混同。

## 2.4 统一实验模板

每组实验按以下顺序报告：

1. 研究问题；
2. 对象与数据来源；
3. 机制和基线；
4. 预注册或事先定义的指标；
5. 结果；
6. 替代解释与威胁；
7. Design Delta；
8. 当前可外推范围。

这一模板专门防止两种常见错误：把测试通过写成理论成立；把大规模合成数据写成现实频率。

## 2.5 概念收敛方法

概念是否成为顶层协议对象，不取决于它是否“重要”，而取决于它是否需要独立的：

- 身份；
- 权威来源；
- 生命周期；
- 版本；
- 撤销；
- 并发控制；
- 跨关系引用；
- 争议与补救。

在此标准下，当前 canonical aggregate roots 维持六类：`Entity`、`Mandate`、`RelationVersion`、`Assertion`、`Commitment`、`Operation`。DataUseEvent 是事件，Derivation 是溯源边，Acceptance 是针对精确 Effect 和 RelationVersion 的 Stance，Settlement 是派生状态。只有当联合制品权利需要独立签发、修改、执行、撤销和争议时，才提升为 Commitment，而不是默认增加 `JointArtifactRights` 根对象。

## 2.6 研究诚实性与可复现性

本研究对三类缺口作显式处理：

- 缺少原始代码或原始结果的历史数字标记为 `reported synthetic evidence`，不以样本量提升等级；
- QDR 受限数据不进入可分享包，正文只报告允许的汇总和方法；
- 公开过程由单一研究者编码的部分，不报告为“客观真值”，并把双人一致性列为后续门槛。

论文随附实验账本、对象 Schema、状态机、参考实现说明、内容损失审计和文件 Manifest。正文足以独立理解主张，附件用于复现和追溯，而不是替正文承担论证。

