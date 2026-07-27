# 审计发现与能力损失清单

## 审计范围

本轮从最新 v1.2 完整包中重建 7 条原生研究线、39 项历史设计能力、22 条主张、16 个证据族
和 15 次设计转折。判断直接引用原包物理路径或 ZIP 成员、SHA-256 与行号。

数量只说明审计覆盖，不说明理论质量。

## 总体结果

| 状态 | 数量 | 含义 |
|---|---:|---|
| PRESERVED | 15 | 原差异、失败检测与行为影响均可人工重建 |
| TRANSFORMED | 5 | 表达改变，但能力可从当前状态与 Gate 完整重建 |
| PARTIAL | 18 | 只有部分场景、阶段或失败仍被覆盖 |
| LOST | 1 | 当前没有承担者，原失败无法由现系统阻止 |
| DUPLICATED | 0 | 本轮未发现必须判为多个正式事实源的能力 |
| UNTESTED | 0 | 已审计行均有足够材料作初步判断 |

`UNTESTED=0` 不表示现实验证齐全，只表示这 39 项能够判断“档案与当前表示的保真状态”。

## 明确丢失

### CAP-REL-004：本地 column generation

后续 `RelationVersion` 能保存候选结果，却没有明确运行机制保存“候选由本地私有行动集生成，
只提交改善当前解的列，中心无权取得完整集合”。这不是术语丢失，而是一个具体能力丢失：

- 当前中心要么依赖主体主动给候选；
- 要么要求更完整的信息；
- 要么无法区分“本地没有路径”和“本地尚未被正确询问”。

恢复动作：建立本地 candidate/counterexample 接口，输出最小贡献、来源、适用版本和不披露
声明；用“移除后中心必须复制全集或错误无解”的反例验收。

## 主要部分损失

### 发现与边界

- HDC 的角色绑定、NAC 的跨模型锚点、前缀预算、SEEK/OFFER 仍可在概念上表达，
  但未成为当前 discovery runtime 的强制行为（CAP-DISC-002/003/004/005）。
- Boundary Oracle 仍被命名，却缺少 cut/witness/unknown/refuse 的完整提升规则
  （CAP-DISC-007）。

### 关系与形成

- Relation Schema 的 materiality 已有定义，但从未经编码现实材料识别它仍未成立
  （CAP-REL-001）。
- JAA 的多作者性被压入 RelationVersion 与事件日志；如果不保存 contribution edge，
  只能回看最终文本，不能按 Authority 重放形成过程（CAP-REL-003）。
- Unknown 路由、countercondition 与形成因果链有策略和局部技术证据，却没有完整运行 Gate
  和真人证据（CAP-FORM-001/002/003）。

### 能力、权威与运行

- prospective holdout、跨伙伴组合容量和漂移资格化只部分进入系统
  （CAP-CAP-002/005）。
- affected-party Standing 进入了理论，但本地发现、代表和 recourse 路径不完整
  （CAP-AUTH-005）。
- Harness 的 Problem/Design/Engineering IR、Context Compiler、Evidence Closure 被统一长文
  描述，却没有由六 roots 承担，也不应该由六 roots 吞并
  （CAP-RUN-001/002/005）。
- Formation Compiler 与 Router 有构造实现；真实复用净值和原材料冷启动判断仍未证明
  （CAP-RUN-003/006）。

## 保真度最高的历史线

现实效力线在整合中损失最少。R5.2 的直接结果迫使系统保留：

```text
ActionAttempt ≠ Effect ≠ Adoption ≠ Acceptance
```

后续虽然把它们实现为 root、event、stance 和派生状态，而不是四个顶层对象，但原差异、目标域
readback、失败检测和行为 Gate 均可重建。因此 CAP-EFF-001 至 CAP-EFF-005 判为
`PRESERVED`。

## 整合真正做对的部分

v0.4 把 PFE、CRA、JAA、Assurance Case、Capability Envelope、Compiled World 从顶层事实对象
降为策略、方法、派生视图或编译产物，本身不是错误。它减少了平行事实源。

错误发生在两种情况：

1. 降级后没有明确运行 owner，导致机制只剩历史名称；
2. 用“可映射到六 roots”替代“原正例和移除失败仍能通过”。

因此恢复方向不是把所有旧缩写重新升为对象，而是为失去 owner 的能力恢复异构内核和共享接口。

## 真正由证据改变的设计

从决策时间线可确认的高价值转折包括：

- R5 的现实成本和事实源问题把默认路由改向最小权限中心；
- R5.2 的 10/17 终态误判催生 Effect Gateway；
- R5.2 capability holdout 使能力 claim 增加环境、权限、版本、恢复和前瞻边界；
- R5.4 把“对话即形成”降级为规范细化；
- R5C 的 producer-only/wrong-authority 失败加入目标域 Authority、负状态和恢复；
- R5C 运行结果支持形成与确定性运行局部分工。

六 roots 的大样本本体收敛、materiality 自评分和作者构造 Router fixture 主要属于
`PREDECIDED_CONFIRMATION` 或 CI，而不是这些层级的判别证据。

## 用户纠正与证据变化

以下是用户改变研究范围或载体，不应冒充实验发现：

- 聚焦 OPC 与 Agent 成为世界行动主体；
- 纠正 27 页压缩论文并要求恢复完整研究；
- 根据审稿停止低信息合成实验并转向 Q1–Q5；
- 本轮冻结新理论，先恢复历史设计能力。

它们记录在 `decision_timeline.csv` 的 `USER_SCOPE_CHANGE`，与
`OBSERVED_DESIGN_FLIP` 分开。

