# 原生研究线 05：权威与规范

## 当时面对的真实问题

模型能提出、预测和执行，不等于它有权代表主体改变目标、承担责任或接受结果。同一个自然人或
组织内部还存在预算、数据、品牌、技术、法律和接受等不同权威位置。该研究线的任务是阻止
“模型认为成立”静默变成“现实中作数”。[SRC-R52-PATCH:3-25]

## 原生机制与能力

### CAP-AUTH-001：Principal 与 Agent Entity 分离

- 区分：对外可认证、持续运行的代理实体，与能产生原生认领并承担责任的规范主体。
- 机制：Entity 指向责任根和 Authority Locus；AgentExecution 只在授权范围内行动。
- 关键决定：认证 Agent 不等于认证其全部观点或目标。
- 正例：一个 OPC 的日程 Agent 可安排会议，但不能因此签署品牌合作。
- 移除失败：工具权限或登录身份被扩大解释为主体的全面代表权。
- 来源：[SRC-V07-OPC:3-54] [SRC-V11-MONOGRAPH:190-220]

### CAP-AUTH-002：范围化、版本化、可撤销 Mandate

- 区分：技术 token 能调用资源，与 Agent 被允许为谁、以什么目的、在何范围内行动。
- 机制：Mandate 绑定 Principal、Authority Locus、目标、动作、资源、数据用途、预算、期限和撤销。
- 关键决定：能力提升不自动扩大 Authority Envelope。
- 正例：只读分析权限允许 probe，但禁止训练、再披露和最终签约。
- 移除失败：有效 token 被当成无限代理权；撤销后旧 Agent 继续执行。
- 来源：[SRC-V07-OPC:3-54] [SRC-V11-MONOGRAPH:2810-2865]

### CAP-AUTH-003：精确版本 Stance

- 区分：对问题的认识、条件性接受、承诺和最终接受。
- 机制：Recognition/Reject/Conditional/Accept 等 Stance 引用精确 RelationVersion 与范围。
- 关键决定：material change 不继承旧 Stance。
- 正例：数据方只接受 no-training v2，不接受 v1 或后续扩大用途的 v3。
- 移除失败：自然语言“同意”被套用到未见过的后续版本。
- 来源：[SRC-TYPED-LEDGER:1-38] [SRC-R52-PATCH:3-25]

### CAP-AUTH-004：Commitment 与资源预留分离

- 区分：表达愿意、承担规范义务与真实时间/预算/容量已被保留。
- 机制：Commitment 引用 RelationVersion、Mandate 和 Reservation；资源冲突进入 Gate。
- 关键决定：没有 reservation 的承诺不能直接进入执行。
- 正例：合作方同意条件，但档期未保留，状态保持 conditional。
- 移除失败：同一预算或时间被多个 Agent 重复承诺。
- 来源：[SRC-TYPED-LEDGER:1-49] [SRC-R5-DECISION:1-99]

### CAP-AUTH-005：受影响方 Standing

- 区分：拥有最终签字权与有资格提出 material challenge、获得代表或补救。
- 机制：Standing 作为 Authority/Relation 属性，记录 challenge、representation 和 recourse 范围。
- 关键决定：没有签字权不等于可以被系统忽略。
- 正例：数据主体或下游受影响方能触发数据用途重审，但不冒充预算签字人。
- 移除失败：双边签署遮蔽第三方外部性，关系被错误编译。
- 来源：[SRC-V11-MONOGRAPH:1700-1730] [SRC-V07-OPC:104-129]

## 后续解释与整合结果

- v0.4 的 `Entity`、`Mandate`、`RelationVersion`、`Commitment` 保住了主要正式状态，
  Recognition/Acceptance 被降为 Stance，避免对象增生。[SRC-V04-ONTOLOGY:36-137]
- v0.7 把一个责任根内多个 Authority Locus、Mandate 版本和 AgentExecution 明确化，
  是 OPC 线最重要的结构性恢复。[SRC-V07-OPC:3-54]
- v1.1 的可执行语义能阻断撤销后动作和错误版本承诺，但真实 OPC 是否能理解、修订和维护
  显式 Mandate 仍没有用户证据。[SRC-V11-MONOGRAPH:2810-2865]

## 当前保留建议

- 正式事实：Entity、Mandate、RelationVersion、Commitment。
- Stance：Recognition、Reject、Conditional、Acceptance，引用精确版本与范围。
- Gate：Authority Locus、撤销、资源预留、Standing。
- 开放问题：显式 Mandate 的认知成本；对抗性参与者的策略披露和选择性认领。

