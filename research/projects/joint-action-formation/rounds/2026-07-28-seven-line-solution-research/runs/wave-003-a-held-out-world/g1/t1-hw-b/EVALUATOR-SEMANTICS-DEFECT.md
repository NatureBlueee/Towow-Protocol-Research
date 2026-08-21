# HW-B evaluator semantics defect

状态：`POST_BLIND_DIAGNOSIS / FUTURE_WORLD_FIX_REQUIRED`  
日期：2026-07-28

## 观察

`candidate-submission-v2.json` 的五条 disclosure 全部来自 Wave-004-B 的真实本地 controller
execution output，而不是手写 completion。controller 已经：

- 写入 HELIOS direct recipient store；
- 原子写入 ION direct + derived onward 的两个 recipient store；
- 原子写入 JUNIPER 与 KITE 的两个 counterparty recipient store；
- 从磁盘 readback 后签发 hash-bound execution receipt。

但 scorer 只给 `4/8`。运行后读取冻结 oracle，发现 method-visible contract 没有公开的三项
语义被 scorer 当成了精确匹配条件：

1. `submission_schema.json` 只规定 `disclosure.depth >= 0`，没有说明它是零起点 hop index，
   还是每次 disclosure 消耗的正整数预算。controller 合理地输出 `0, 0, 1`；scorer 隐含要求
   每条 event 都是 `1`。
2. reciprocal exchange 是双向对称完成，但 method-visible contract 没有规定哪一方必须写
   成 `requester`、哪一方必须写成 `responder`。scorer 隐含要求 OFFER 侧为 requester。
3. probe `status` 只要求非空字符串，没有公开枚举。controller-derived adapter 使用
   `COMPLETED_RECIPROCAL_RECEIPT`；scorer 隐含要求 `RECIPROCAL_COMPLETE`。

scorer 也不验证 controller execution receipt、authoritative event、recipient readback 或 state
root。因此 scorer 的 `8/8` 即使将来出现，也只能说明 candidate 使用了 evaluator 预期表示，
不能单独证明执行真实发生。

## 结论边界

这不是“controller 已经完美、只是 scorer 错了”，也不是“把字段改成 oracle 期待值就获得新的
盲测成功”。

- V2 的 `4/8` 必须保留为第一次真实 controller-derived development score。
- 后续 V3 只用于区分“执行机制缺口”与“未公开表示约定”；它明确使用了 post-oracle feedback，
  不能算 blind、independent 或新的 held-out evidence。
- derived onward 仍只在 trusted controller 被合成 contract 授权代表 first recipient 的模型中
  成立；没有 recipient 签名 ACK。

## 对下一留出世界的强制修正

HW-C 在冻结前必须公开：

- `depth` 的单位、起点、逐 event 与累计计算方式；
- reciprocal requester/responder 的方向约定，或把对称 exchange 改为无方向 pair schema；
- probe status 的闭合枚举与状态转换；
- scorer 如何验证 controller event、execution receipt、recipient readback 与 state root。

否则 evaluator 继续测量隐藏格式约定，而不是方法是否解决原问题。

## Post-oracle 诊断结果

`build-candidate-v3-post-oracle.py` 没有改变任何 route、fact、recipient、purpose、retention、
event ID、parent link、decision 或 handoff，只做三项表示映射：

- controller hop depth `0/1` → scorer disclosure-budget depth `1/1`；
- 从已执行 exchange 的 OFFER/SEEK 方向导出 requester/responder；
- `PERFORMED + 双 recipient readback` → scorer label `RECIPROCAL_COMPLETE`。

结果：

| candidate | 性质 | score |
|---|---|---:|
| V2 | controller-derived，未读 oracle 的 development result | `4/8 = 0.50` |
| V3 | post-oracle representation diagnosis | `8/8 = 1.00` |

V3 candidate SHA-256:
`d9c39e391d02b871b9d989f4a7f748d7c49e69c20d847ea5dc7b1d4ee119da42`

V3 score SHA-256:
`ab79779ab20b6f9187b23ab849c3e50699a50c1051b7c7463f85f24e6545e9f3`

这个结果支持一个窄判断：

> 在当前合成世界和 trusted-controller 边界内，V2 剩余的 scorer 差距可由三项隐藏表示约定
> 完全解释；没有观察到还需新增搜索、匹配或 route 机制才能通过这八项要求。

它不支持“HW-B 已被第二次盲测通过”，也不支持现实跨 Authority 执行已经成立。
