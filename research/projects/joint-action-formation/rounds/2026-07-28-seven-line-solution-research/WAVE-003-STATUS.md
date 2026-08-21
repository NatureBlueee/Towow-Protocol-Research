# Wave 003：当前研究状态

状态：`ACTIVE / NOT_COMPLETE`  
日期：2026-07-28  
入口假说：`WAVE-003-CONSTRUCTION-HYPOTHESIS.md`

本页只记录会影响下一步研究的最小状态，不把测试数量或文档完整度当作问题解决。

## 已得到的结果

### T5：现成平台完整胜出是正向结果

第一版 evaluator 已被独立反例推翻：一个只声明 `PLATFORM_DIRECT`、没有执行任何动作的候选
曾获得 `6/6 PASS`。该结果无效，完整失败记录保存在
`tasks/t5-collapse-safe/FIRST-EVALUATOR-FAILURE.md`。

V2 又被第二轮独立攻击推翻：adapter 的 authority、写入、cache、泄漏和成本仍靠候选自报；
错误前置链还会被 simulator 伪装成注入的 failure terminal。完整反例保存在
`tasks/t5-collapse-safe/SECOND-EVALUATOR-FAILURE.md`。

V3 只接受 hash 绑定且由 evaluator 解释执行的 bounded JSON transducer；披露从执行 trace
重建，成本从 trace 推导，failure 只有在有效前置链真正到达时才成立，handler 必须执行
readback 后停止且不 retry。第三轮独立攻击没有在冻结作用域内找到可满分的实质伪成功。
当前同一分母结果是：

| 方法 | 结果 | 当前能说明什么 |
|---|---:|---|
| 现成平台直接执行 | `6/6 PASS` | 当前合成任务不需要新增协议机制 |
| hash 绑定的 reference identity adapter | `6/6 PASS` | 该特定受限 transducer 可在不复制事实源的前提下薄封装现成平台 |
| 只贴强中心标签、零动作 | `INVALID` | 方法名称和自报 truth source 不是任务完成 |

这是通爻组合方案的正向结果：问题被现有平台完整解决，因此正确设计是收敛到现有平台，而
不是为了原创继续制造机制。adapter 结论只适用于“固定平台 + evaluator 白名单 identity
transducer”，不是通用 adapter verifier；handler receipt 仍由 evaluator 解释生成。它还
没有证明真实采购、支付、生产可靠性或跨平台迁移。

### T2：bounded probe 从“未运行”推进到可区分的执行证据

冻结模拟器覆盖五个分支：

- 成功；
- 环境不匹配，执行前阻断；
- credential 在运行中撤销；
- producer 完成但 buyer-domain witness 缺失；
- 重复重试，只返回既有 receipt，不产生新执行。

模拟器把 `ActionAttempt`、buyer witness、idempotency、recovery 与 hash receipt 分开。
probe-to-relation bridge 只允许成功分支资格化**精确冻结的合成 probe operation**，不允许
推出正式 pilot、业务 Effect、Adoption、Acceptance 或 Settlement。环境不匹配只重开环境
binding；撤销要求新授权；缺 witness 不能形成 reliance；重复重试不增加证据。

这说明 receipt-backed probe 可以缩小 Unknown，但 probe 成功与关系成立、任务效果之间仍有
必须继续取得的 Authority stance 和目标域证据。

### G1：新的留出世界已经冻结，但候选尚未运行

`T1-HW-B` 已完成 method-visible contract、分主体物理隔离 packet、独立 oracle/scorer、
动态失效和九类负 mutation。校准 fixture 能通过 `8/8`，13 项隔离与变异测试通过。首个候选
已由每 packet 一个独立 holder、coordinator 综合并交给 scorer：

| 指标 | 结果 |
|---|---:|
| correctly discovered opportunities | `3/3` |
| opportunity recall | `1.0` |
| false wakeup | `0` |
| requirements | `1/8 PASS` |

语义匹配找对了全部三个机会，也没有 decoy 误唤醒；但候选把 holder 的
`AUTHORIZED / NOT_FORWARDED / NOT_PERFORMED` 擅自升级成已完成 route/probe，并引用自造
event/probe ID。只有 R5 通过；其余要求因缺 disclosure path、reciprocal completion 和冻结
evidence 失败。

truth owner 随后也一度手写 completion JSON，复核后确认仓库没有实际 controller executor、
receipt issuer 或既有执行日志，立即撤回并删除。当前正确状态是：

> `FAIL_1_OF_8 / BLOCKED_BY_MISSING_CONTROLLER`

下一步必须先实现并冻结实际 controller state machine、route/probe executor、idempotency 与
权威 receipt issuer；不能在 HW-B 手写回执后冒充第二次盲测。

### T4：三主体联合投标的盲任务已经冻结

新任务允许人工 broker、强中心模型、CMMN/BPMN/DMN、IAM/policy、成熟 workflow 或其他组合
获胜。它检验当前 tender、私有 column、跨主体 probe、分立 Authority、resource reservation、
submission/Adoption/Acceptance/Effect 分离、scoped reopen 与异行业迁移。

任务结构、controller、迁移变体和 G2–G7 mutation closure 已通过校验。本地 method-neutral
基线已在不读取 oracle 的情况下完成两轮 controller 交互：

- 31 个 receipts，其中 3 个前置不足先 `DEFER`、第二轮才成功；
- exact synthetic interop probe 得到有界 witness；
- PRIME、FIELD、ASSURE 三项资源 reservation 绑定同一 relation version；
- 组合报价 335000 CNY，低于 360000 CNY 上限；
- 候选保持 `CANDIDATE_NOT_COMMITMENT`，没有声称真实签署、提交或城市效果。

候选 SHA-256 为
`b7b9fc972b3c051841a37cc3af6a80f80459e0faf7458c57bffdb63737f2fd5a`，
schema validation 已通过。隐藏 truth/mutation/migration 的独立评价结果为
`0.60 / PARTIAL`：

- R6 outcome/readback：`PASS`；
- R2/R3/R4/R5/R7：`PARTIAL`；
- 无外部 outcome false closure，也无 critical `FAIL`；
- mutation：`3 PASS / 4 PARTIAL / 3 UNKNOWN`，未闭合；
- migration：`UNKNOWN / NOT_RUN`。

最重要的失败不是技术链不存在，而是候选把 `ALL_DISCLOSED_CONDITIONS_SATISFIED` 写得过强：
FIELD 风险分配和 ASSURE audit scope freeze 没有 Authority 证据；预算变化、签署撤回、
probe fail 和重复 portal submission 的 transition/reopen 也不完整。当前状态是：

> `LOCAL_BASELINE_PARTIAL_0.60 / CONSTRUCTION_CONTINUES`

对 OpenAI 外部求解实例的发送仍被当前审批边界阻止；这只阻塞另一条外部模型盲解，不影响
本地基线与本地独立 evaluator。

## 七目标当前含义

| 目标 | 当前变化 | 尚未解决 |
|---|---|---|
| G1 Discovery before search | HW-B 语义召回 3/3、false wakeup 0 | 仅 1/8；缺实际 controller/receipt issuer |
| G2 Relation from task | probe 后只允许请求 stance；T4 已形成非承诺候选 | exact role/responsibility/exit 仍不完整，R2 PARTIAL |
| G3 Form reachability | T4 的 3 个 DEFER 在前置披露后变为 probe/reservation witness | transition table、withdrawal 和 duplicate submission 不完整 |
| G4 Capability to reliance | 精确 probe operation 可被有界资格化 | 未证明业务能力与持续 reliance |
| G5 Authority composition | T4 基线分别请求技术、价格、签署、资源与城市 Authority | 风险分配与 audit scope freeze 缺 Authority 证据，final signatures 未发生 |
| G6 Effect that counts | Effect/Adoption/Acceptance/Settlement 均保持未建立 | 仍缺目标 Authority 现实 readback |
| G7 Reuse and safe reopen | 五分支 bridge 只重开受影响依赖；T4 有部分规则 | mutation 未闭合，migration 未运行 |

## 防止旧错误再次发生

- 只把根 `AGENTS.md` 作为用户所说的 `agent.markdown` 指令载体，不再扩写专名；
- 现成平台、强中心、通用模型或组合完整解决任务时，登记为通爻正向方案；
- evaluator 必须检测真实执行或权威 postcondition，不能奖励方法标签；
- 同一已揭示 world 上的修补不能冒充新的盲分；
- synthetic runner、same-model evaluator 和 test green 只支持其冻结作用域；
- `Probe → capability → relation → Effect` 之间不允许自动升级；
- 尚未运行的候选一律保持 `UNKNOWN`。

## 下一步

1. 保留 T5 V1/V2 两次 evaluator 失败，并把 V3 的 claim 固定在当前可执行验证作用域；
2. 在不读取 oracle 的条件下运行 T1-HW-B 本地确定性组合候选；
3. 冻结并独立评价 T4 本地 method-neutral 基线，再在获得精确外发许可后运行独立模型盲解；
4. 把 T2 bridge 接入 T4 的 probe、Authority stance 与 versioned handoff，检验能否真正形成
   可提交候选；
5. 所有新结果继续使用相同任务分母比较单项、两项组合和更复杂组合，复杂度增加但分数下降
   也作为一等负结果保留。
