# 原生研究线 06：现实效力

## 当时面对的真实问题

Agent 系统常把退出码、日志、文件生成或 Task completed 当作现实完成。R5/R5.2 直接检验这种
压缩是否安全，并发现操作尝试、目标世界变化、采用和主体接受必须分开；否则系统会稳定地把
“做过”写成“作数”。[SRC-R52-EFFECT:3-35]

## 原生机制与能力

### CAP-EFF-001：ActionAttempt 与 Effect 分离

- 区分：执行器尝试了动作，与目标世界状态确实改变。
- 机制：Operation 产生 ActionAttempt；Effect 由目标世界 witness/readback 建立。
- 关键决定：执行器日志不能单方面创建 Effect。
- 正例：R5.2 中 naive 终态标签在 17 个场景错 10 次，而同一 readback 规则重建 17/17。
- 移除失败：exit 0 或 producer “done” 被写成现实完成。
- 来源：[SRC-R52-EFFECT:3-35] [SRC-R52-PATCH:3-35]

### CAP-EFF-002：目标域权威 readback

- 区分：原始字节、producer JSON、consumer 可读事件与目标域权威状态。
- 机制：按 authoritative source 顺序读取目标状态，并保留 provenance。
- 关键决定：readback 由目标域定义，不由调用方选择最方便的日志。
- 正例：raw bytes 不是可读事件，修复 Event writer 后才形成可消费记录。
- 移除失败：目标域未读取或格式错误，调用方仍报告成功。
- 来源：[SRC-R52-EFFECT:37-57] [SRC-R52-EFFECT:94-115]

### CAP-EFF-003：Effect、Adoption、Acceptance 分离

- 区分：世界发生变化、目标系统采用变化、相称主体认为结果满足关系。
- 机制：Effect receipt、Adoption 状态和 Acceptance Stance 分别引用来源与版本。
- 关键决定：任何一层都不能由上一层自动推出。
- 正例：`applied` 可以早于实际 consumption；技术 adoption 也不能替代人类接受。
- 移除失败：系统已经写入目标域就自动结算，忽略未采用或未接受。
- 来源：[SRC-R52-EFFECT:72-92] [SRC-R5C-HUMAN:1-23]

### CAP-EFF-004：负状态与撤销是一等事实

- 区分：未观察到成功，与明确 not_adopted、revoked、offline 或 disputed。
- 机制：保存负状态、来源、版本和时间，不以删除正记录表示撤销。
- 关键决定：撤销和未知不能压成 `success=false`。
- 正例：R5C 的 adopted→revoked→offline/unknown→adopted 保留同一 projection identity。
- 移除失败：旧正状态继续驱动下游，或恢复时产生第二身份。
- 来源：[SRC-R5C-SUMMARY:39-51] [SRC-R5C-PATCH:1-53]

### CAP-EFF-005：恢复与 replay identity

- 区分：重试制造新动作与对同一 Operation/Projection 的恢复。
- 机制：幂等 identity、版本、recovery receipt 和目标域 readback。
- 关键决定：恢复必须可关联原尝试与原责任链。
- 正例：offline 后恢复同一 adopted projection，而不是创建重复采用。
- 移除失败：重试造成重复副作用、重复结算或不可追责的第二结果。
- 来源：[SRC-R5C-SUMMARY:39-57] [SRC-R5C-METHOD:36-53]

## 原始证据与反例

R5.2 是本线最强直接证据：17 个真实 Harness 场景中 naive 标签错 10 次；相同的四阶段
authoritative readback 规则得到 17/17。它同时保留了 `applied` 早于消费和 raw bytes 不是事件
的反例，因此结论不是“增加四个顶层对象”，而是“语义差异必须可重建”。
[SRC-R52-EFFECT:3-126]

R5C 进一步接触目标域 adoption、revoke、offline 和 recovery；producer-only 和 wrong-authority
消融失败，说明目标 witness 与权威位置不是装饰。[SRC-R5C-ABLATION:3-27] 但 R5C 没有人类
Acceptance 证据。[SRC-R5C-HUMAN:1-23]

## 后续解释与整合结果

v0.4 将 Effect 保留在 Operation 结果/事件链，将 Acceptance 作为 Stance，避免四个平行事实根；
只要来源与生命周期可重建，这属于保真转换。[SRC-V04-ONTOLOGY:36-137] v0.7/v1.1 的
Effect Gateway、Acceptance Console 与 scoped reopen 延续了这条链，是三次整合中保真度最高
的研究线。[SRC-V07-OPC:56-73] [SRC-V11-MONOGRAPH:2810-2865]

## 当前保留建议

- 正式事实：Operation、ActionAttempt event、Effect receipt。
- Stance/派生：Adoption、Acceptance、Settlement，均引用目标来源和精确版本。
- 强制 Gate：无目标域 witness 不得把 Attempt 提升为 Effect。
- 开放问题：真实主体的 Acceptance、长期后悔和净价值。

