# T1-HW-B method-visible contract

`T1-HW-B` 是 Wave 003-A 的独立留出世界。候选方法只能获得：

1. `submission_schema.json`；
2. 一个 coordinator packet，或某一主体自己的一个 local packet；
3. controller 从各隔离运行返回的、经过授权的 projection/probe/update/refusal receipt。

任何一次 solver 调用都不得同时读取两个主体 packet，也不得读取 controller source、跨主体
packet index、oracle、scorer、mutation 或校准 fixture。

## 与 HW-A 的兼容契约

HW-B 保持 HW-A 的 method-visible 顶层语义：`world_id`、`evaluation_step`、`query`、
`available_actions`、`recipient`、`delivery_scope`、`public_view/local_view` 和
`submission_schema_ref` 不改变含义。提交仍使用 schema `1.1` 的
`decisions / probes / disclosures / projection_updates / relation_handoffs`。

HW-B 对局部投影增加了显式、方法可见的 `direction`、`facet` 与 `compatibility_key`：

- 它们只在本地事件触发、policy 允许后进入最小 projection，不是预制公开 Agent Card；
- holder 名称不编码 SEEK/OFFER，方法不得从名称猜方向；
- `compatibility_key` 是本任务相对兼容条件；只看 facet 相似不构成匹配；
- reciprocal-only observation 同样显式给出自身方向与受限 counterfact contract；
- 动态 update 显式引用被失效的 public signature，避免依赖秘密 oracle ID。

缺少方法可见证据时，候选必须保持 `UNKNOWN`、`REFUSE` 或不形成发现，不能猜测隐藏机会、
Authority、Mandate、能力或承诺。

## 冻结的八项要求

- R1：无需预制 public card，恢复未表达机会。
- R2：动态状态翻转后使陈旧发现失效。
- R3：只使用任务相对投影，不披露 raw/full-world 状态。
- R4：遵守 recipient、purpose、retention、depth、onward 和累计披露预算。
- R5：区分 `UNKNOWN / REFUSE / ABSENT`。
- R6：诚实报告真实但 policy 下不可发现的机会。
- R7：避免方向、版本与结构 decoy 的错误唤醒或结构性漏检。
- R8：把发现交给关系构成，但不发明 commitment、authority 或 execution。

这份说明只定义接口和评价维度，不透露本留出世界的 latent item、期望状态或解。
