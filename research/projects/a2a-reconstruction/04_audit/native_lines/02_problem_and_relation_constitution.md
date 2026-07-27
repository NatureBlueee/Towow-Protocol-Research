# 原生研究线 02：问题与关系构成

## 当时面对的真实问题

传统匹配和编排假定角色、变量、动作、约束和评价函数已经存在。第二轮研究指出，开放协调中
这些内容可能需要在互动里形成；因此问题不只是“搜索哪个候选”，而是“形成可以被搜索和执行
的关系语言”。[SRC-ROUND2-PAPER-I:1-20]

## 原生机制与能力

### CAP-REL-001：关系语法本身可变化

- 区分：在固定 Schema 中改参数，与新增角色、动作、权威、证据或退出路径。
- 机制：Coordination Schema 显式承载角色、变量、动作、约束和 evidence rule。
- 关键决定：把 Schema 作为形成对象，而不是协调器的隐藏假设。
- 正例：数据上传方案变为代码进入买方域，改变动作、数据位置、witness 和接受条件。
- 移除失败：系统把制度变化当成价格或字段更新，继续执行陈旧流程。
- 来源：[SRC-ROUND2-PAPER-I:1-20] [SRC-ROUND2-PAPER-II:270-320]

### CAP-REL-002：版本化 Coordination IR

- 区分：当前提案、旧提案和各方真正认领的精确版本。
- 机制：每次 material change 产生新版本，旧版本可追溯但不可静默继承 Stance。
- 输入：候选、约束、证据、参与角色。
- 输出：可引用的协调版本。
- 关键决定：修改产生新身份；承诺引用精确版本。
- 正例：一方只认领加入 no-training 条款后的版本。
- 移除失败：自由聊天里“原则同意”被错误套到后续改写方案。
- 来源：[SRC-TYPED-LEDGER:1-38] [SRC-R52-PATCH:3-25]

### CAP-REL-003：JAA 作为多作者共同对象

- 区分：一份中心摘要与由多个权威分别贡献、反对和认领的共同制品。
- 机制：JAA 保存来源、条件、未决项、版本和局部 Stance。
- 关键决定：共同对象不等于共同世界模型；各主体只对自己的范围作数。
- 正例：技术方认领可运行性，数据方认领数据边界，业务方保留最终采用权。
- 移除失败：中心 Agent 的统一总结吞掉异议来源和范围差异。
- 来源：[SRC-ROUND2-PAPER-I:250-275] [SRC-ROUND2-PAPER-II:270-320]

### CAP-REL-004：隐藏贡献的 column 机制

- 区分：披露完整私有选项集合与只提交能改善当前解的候选列。
- 机制：本地 Oracle 生成 column/counterexample，中心只接收必要贡献。
- 关键决定：候选生成留在本地，协调器不要求全局枚举。
- 正例：主体不公开全部资源，只提交满足当前缺口的一种组合。
- 移除失败：中心必须复制私有行动集，或因没有完整集合而宣称无解。
- 来源：[SRC-ROUND2-PAPER-I:490-520] [SRC-ROUND2-PAPER-II:270-320]

### CAP-REL-005：候选与承诺分离

- 区分：模型生成的候选关系，与由有权主体承担的承诺。
- 机制：typed ledger 把 candidate、evidence、recognition、commitment 分层；候选不能直接执行。
- 关键决定：从 proposal 到 commitment 必须经过相称 Authority 的 Gate。
- 正例：模型提出合作路径，但预算方拒绝资源预留，关系保持候选。
- 移除失败：高置信候选静默变成真实义务。
- 来源：[SRC-TYPED-LEDGER:1-49] [SRC-R52-PATCH:3-25]

## 后续解释与整合结果

- v0.4 将 JAA 映射为 `RelationVersion`，保住了版本与引用，但没有自动保住生成 Schema 的求解
  过程、隐藏 column 和多作者范围语义。[SRC-V04-ONTOLOGY:197-253]
- v0.7 明确 Relation Schema 与完整生命周期，关系语法变化重新进入系统；同时仍以六 roots
  保存正式状态。[SRC-V07-OPC:56-129]
- v1.1 的 Relation Workspace 能表达版本与 Stance，但“原始问题语法如何在互动中形成”仍主要
  是策略层，缺少从原始材料冷启动推断的证据。[SRC-V11-MONOGRAPH:2810-2865]

## 当前保留建议

- 事实对象：`RelationVersion` 及精确版本 Stance。
- 运行时：material-change Gate、版本依赖、旧版本失效。
- 方法：Schema 形成、column generation、JAA 工作台保留为异构机制，不能被一个 content 字段替代。
- 研究假说：Router 能否从未经编码的现实输入判断何时 Schema 未形成，仍开放。

