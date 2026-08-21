# 第一版 evaluator 的失败

第一版 T5 evaluator 已判定无效，不得引用其 6/6 结果。

独立攻击构造了两个 schema 合法反例：

1. `mode=PLATFORM_DIRECT`，但 `steps=[]`、没有购买/支付/provision，只自报 platform truth source
   和 readback 字段名，仍得到 6/6；
2. 把 shadow ledger、长等待、模型 recovery 和敏感字段藏进少数自由文本 step/field alias，
   仍得到 6/6。

它还错误拒绝了 PROGRAM 允许的真正无状态轻 adapter。根因是评价标签、字符串和数组长度，
没有运行购买任务，也没有平台权威 receipt。

V2 修复为：

- schema 实际校验；
- 六个结构化 operation 的权威平台状态机；
- exact SKU、seat、price、approval、payment、provision 和 postcondition；
- 四个失败 mutation；
- exact disclosure allowlist；
- 派生的 wait/human/cognition/governance/recovery 成本向量；
- 允许经过验证的 stateless、non-authoritative adapter。

这个错误被保留，是为了防止后续再次把“写了正确标签”当作 collapse-safe。
