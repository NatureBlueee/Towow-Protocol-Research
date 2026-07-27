---
derived_view: true
source_path: Towow_Complete_Research_Archive_v1.2_2026-07-27/02_WORKSPACE_SNAPSHOT/Towow_R8_OPC_Constructive_Closure_v1.1/human_study/通爻_OPC真人实验完整方案书_v1.1.md
source_sha256: 926abf8a318a47130e0bf39395421eb47ca29cfc250ad5dcb04f73fc2eb6b05f
source_line_start: 624
source_line_end: 674
source_heading: "11　多 Agent 协同设计"
---

> 本文件是导航用派生视图。原始文本未改动；引用研究证据时应回到上列源文件与行号。

# 11　多 Agent 协同设计

## 11.1 逻辑角色

以下是逻辑职责，不要求每个职责由独立模型进程实现：

1. **Owner/Principal Interface Agent**：采访目标、边界和角色，生成 explain-back；
2. **Boundary Agent / Local Oracle**：在本地域回答任务相关边界，不泄露完整世界；
3. **Opportunity/Problem Agent**：发现关系、重构问题、生成候选；
4. **Formation Agent**：提出 probe、countercondition、任务拆分、伙伴/工具引入；
5. **Capability & Assurance Agent**：区分自报能力、sandbox 结果和 Qualified capability；
6. **Router/Broker Agent**：选择平台、中心优化、人类经纪、双边形成或联盟的组合；
7. **Mandate/Policy Agent**：把自然语言授权编译为机器 Gate；
8. **Commitment/Reservation Agent**：绑定精确版本并原子预留时间、预算和容量；
9. **Execution Agent**：在 Mandate 下调用工具；
10. **Effect Witness Agent/Connector**：从目标域读取状态，不接受执行方自证；
11. **Acceptance Agent**：收集相称 Principal 对 Effect/版本的接受、保留或拒绝；
12. **Auditor/Adjudicator**：检查来源、冲突、争议、事件链和补救。

## 11.2 交互原则

- Agent 只能提出 Candidate，不得把模型置信度写成 Authority；
- 任何跨责任根 material message 必须引用 RelationVersion；
- 本地 Oracle 可以返回 hard cut、empirical boundary、model objection、human refusal、unknown、contribution column 或 witness；
- 拒绝必须保留原因范围，允许产生 countercondition，但不得被模型反复诱导；
- 形成动作必须可定位和可消融；
- Commitment 前必须完成必要 Recognition、资源预留和 data-rights Gate；
- Operation 与 Effect 使用不同事件；
- Adoption 与 Acceptance 使用不同 Stance；
- 中心 Agent 可以计算候选，但不得静默改变本地权威；
- 稳定子图可以编译，Defeater 只重开依赖闭包。

## 11.3 典型跨 Agent 流程

```text
Principal A -> A 的 Owner Agent：表达事项和边界
A 的 Boundary Agent -> Router：任务相关能力/限制摘要
Router -> 候选平台、经纪或 Entity B：发现请求
B 的 Boundary Agent -> Relation Workspace：条件、拒绝或 Unknown
Formation Agent -> 双方：最小 probe / countercondition
Capability Agent -> RelationVersion：probe witness 与保障级别
Mandate Agent -> 各本地 Gate：精确授权草案
Principals -> RelationVersion：Recognize / Conditional / Reject
Reservation Agent -> 本地资源：原子预留
Execution Agent -> 目标系统：Operation
Effect Connector -> Event Graph：目标世界 readback
Acceptance Agent -> Principals：Effect 差异与接受范围
Compiler -> 稳定子图：确定性运行工件
Defeater Monitor -> 依赖图：局部 reopen
```

