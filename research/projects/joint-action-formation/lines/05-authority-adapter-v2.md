# 研究线 05-V2：版本化权威差异的最小适配器

Contract：`LINE-05-AUTHORITY-ADAPTER-V2 / v1`

状态：`ACTIVE`。本状态只激活 `E-AUTH-01-ADAPTER-SUFFICIENCY` 的本地 policy/transition
fixture 与现成方案组合研究；它没有建立任何现实主体的授权、承诺、接受或责任。

强基线不是弱化的 RBAC。`MATURE-STACK` 必须同时获得 RBAC、ABAC、ReBAC、scoped
delegation、approval、contract/version、reservation 与 append-only audit；`MANDATE-ADAPTER`
只能在相同底层事实之上增加最小 AuthorityLocus、Mandate、RelationVersion/Stance 或
Standing 映射。若 adapter 复制 IAM、合同、workflow、reservation 或 audit 的事实，它即
失败，因为这会制造第二授权现实。

本线立即测试同一 authenticated Entity 内能力相同但 authority locus 不同的角色，以及
purpose/data 越界、material relation version 变化、撤销并发、Commitment 已存在但
reservation 失败、受影响方 challenge 等 transition。Policy decision、实际 operation 与
postcondition 必须分别 readback；一个 `Allow` 不得自动建立 Commitment、Reservation、
Effect 或 Acceptance。

现成标准和平台已经覆盖角色、属性、关系、细粒度授权、委托、credential 与人工 Gate 的
大量能力，因此 disposition 为 `EXTEND`，不是 `NEW_GAP`。当前残余问题只包括：谁产生并
认领 policy 所需事实；material change 怎样使旧 Stance 失效；无签字权受影响方怎样获得
Standing；不同生命周期状态怎样保持分离。

## 明确未启动

`E-AUTH-02-MANDATE-EXPLAINBACK` 状态为 **`DEFERRED`**。本合同不招募真人、不展示或收集
私人 Mandate、不让 synthetic participant 或模型替人复述，也不从历史真人方案推断当前
主体理解、自由认领或愿意承担责任。

现实 Principal 授权、Mandate 签署、Commitment、Acceptance、法律有效性、公平性、外部
消息和生产策略写入均 **未启动**。任何需要这些状态的行动必须建立独立场景、材料边界、
退出机制和用户明确授权；本线的 `ACTIVE` 不能被用作授权来源。

本线的机器结果最多更新 `SC-AUTH-VERSIONED-ADAPTER-GAP`。它不能证明真人可理解性、现实
规范有效性、Capability、关系形成、Effect、Adoption、Settlement 或通爻整体净价值。
