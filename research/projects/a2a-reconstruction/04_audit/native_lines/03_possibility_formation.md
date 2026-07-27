# 原生研究线 03：可能性形成

## 当时面对的真实问题

“当前没有可行方案”可能来自真实不可能，也可能来自缺少工具、伙伴、授权、证据、任务重构或
现实试验。若系统只在已有候选中搜索，它会把暂时不可达误写成永久不可达。PFE、probe 和
countercondition 用于改变可达行动集，而不是替主体宣布能力已经形成。
[SRC-ROUND2-PAPER-I:490-520] [SRC-R52-CAPABILITY:76-97]

## 原生机制与能力

### CAP-FORM-001：Unknown 类型化路由

- 区分：缺信息、缺能力、缺权限、缺证据、被拒绝和结构性不可能。
- 机制：Unknown 带类型与责任位置，路由到 ask、probe、tool、partner、authority 或 task rewrite。
- 关键决定：`UNKNOWN` 不是一个终态标签。
- 正例：能力未知触发 sandbox probe，而不是继续自然语言协商。
- 移除失败：所有 Unknown 都被当作补资料问题，系统无限追问或错误拒绝。
- 来源：[SRC-ROUND2-PAPER-II:270-320] [SRC-R52-CAPABILITY:76-97]

### CAP-FORM-002：形成动作改变可达集合

- 区分：发现原本存在的路径与通过动作创建新的合格路径。
- 机制：显式记录前态、formation operator、后态和必要条件。
- 关键决定：形成主张必须能被消融；文本增量不自动算形成。
- 正例：加入目标域 readback、恢复和权限后，原本不能安全采用的 adapter 变为可运行。
- 移除失败：删除关键 operator 后路径仍成立，说明只是发现或解释。
- 来源：[SRC-R5C-FORMATION:1-27] [SRC-R5C-ABLATION:14-27]

### CAP-FORM-003：countercondition 把拒绝转为可构造缺口

- 区分：无条件拒绝与带最小可满足条件的拒绝。
- 机制：拒绝方返回不泄露完整世界的 countercondition；协调器修改角色、任务或证据。
- 关键决定：拒绝权保留在本地，countercondition 不等于接受。
- 正例：拒绝原始数据导出，但允许买方域内只读执行。
- 移除失败：协调器在“接受/拒绝”二元状态中终止，本可构造的路径消失。
- 来源：[SRC-ROUND2-PAPER-II:270-320] [SRC-R54-CAUSALITY:13-40]

### CAP-FORM-004：现实 probe 而非语言自报

- 区分：主体声称可能做到与在限定环境中产生可观察结果。
- 机制：低风险、可逆 probe，绑定环境、权限、版本和 witness。
- 关键决定：能力未知优先由最小判别动作解决。
- 正例：held-out adapter 在冻结条件下运行并由目标域读回。
- 移除失败：仅凭模型自报或静态安装状态授予能力，出现假能力。
- 来源：[SRC-R52-CAPABILITY:3-26] [SRC-R5C-HOLDOUT:1-27]

### CAP-FORM-005：形成的使用与停止条件

- 区分：需要开放形成的关系与已经适合中心/确定性机制的关系。
- 机制：当问题结构、权威和 Effect 条件未闭合时形成；闭合后编译或交给更简单机制。
- 关键决定：形成不是默认永久运行方式。
- 正例：新反例出现时只重开相关局部；稳定路径继续确定性运行。
- 移除失败：所有任务持续多 Agent 协商，成本和漂移上升；或所有任务提前固化，漏掉新路径。
- 来源：[SRC-R5C-METHOD:36-62] [SRC-R54-NET:1-64]

## 原始证据与反例

- R5.4 是关键负结果：真实模型互动增加了规范条件，但没有签署、代码补丁、目标域采用或新
  现实能力；中心路径还因 transport failure 缺席。因此它反驳“更多对话就是形成”，但不能
  证明联邦优于中心。[SRC-R54-CORE:41-89] [SRC-R54-CAUSALITY:3-80]
- R5C 提供局部技术域正结果：probe、权威拒绝、最小 countercondition、目标 readback、撤销和
  恢复构成一条新路径；producer-only 和 wrong-authority 消融失败。[SRC-R5C-SUMMARY:10-69]
  [SRC-R5C-ABLATION:3-38]
- R5C 没有真人 Principal、商业净值或匹配的强中心形成基线。[SRC-R5C-HUMAN:1-23]

## 后续解释与整合结果

v0.4 把 PFE 归为策略/处理过程，这是正确的对象层降级；但如果运行时只保存最终
`RelationVersion`，形成动作的因果链会被压掉。[SRC-V04-ONTOLOGY:197-253] v0.7 和 v1.1
重新加入 formation planner、probe 与能力组装，但真实 causal formation 仍未通过 Q4 人类
Principal 证据门。[SRC-V07-OPC:56-73] [SRC-V11-MONOGRAPH:2970-3030]

## 当前保留建议

- 运行时：Unknown 类型、probe、countercondition、前态/后态、operator provenance。
- 策略：PFE 作为可替换形成策略，不作为事实根。
- 研究假说：真人事项中形成动作是否有正净增量；在此之前状态为局部技术证据支持。

