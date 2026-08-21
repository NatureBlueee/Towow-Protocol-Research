# G1 T1-HW-B first held-out run

状态：`FAIL_1_OF_8 / BLOCKED_BY_MISSING_CONTROLLER`  
日期：2026-07-28

## 冻结结果

- candidate: `runs/wave-003-a-held-out-world/g1/t1-hw-b/candidate-submission-v1.json`
- candidate SHA-256:
  `91752ae95fd61c2c920152e766fa37821ff855deaaec87e7e7660002ac632b49`
- score: `runs/wave-003-a-held-out-world/g1/t1-hw-b/candidate-score-v1.json`
- score SHA-256:
  `bf71176bb9689b8cefd57a4d48ccb85add8a916f5924875e44cf6618ef6f7c46`

同一冻结世界结果：

| 指标 | 结果 |
|---|---:|
| correctly discovered opportunities | `3/3` |
| opportunity recall | `1.0` |
| false wakeup | `0` |
| requirements | `1/8 PASS` |

只有 R5（`UNKNOWN / REFUSE / ABSENT` 区分）通过。R1/R2/R3/R4/R6/R7/R8 失败。

## 为什么“找对了”仍然只得 1/8

holder 隔离运行正确产生了：

- HELIOS/ION 的两个互补 task-relative projection authorization；
- JUNIPER/KITE 的两个 reciprocal probe offer authorization；
- DELTA 的版本失效；
- GLASS 的 policy refusal；
- LUMEN/MESA/closed cohort 的认识论状态 receipts。

候选正确映射了三个 discoverable opportunity，也没有 false wakeup。但它犯了一个承重错误：

> 把 `AUTHORIZED / NOT_FORWARDED / NOT_PERFORMED` 写成了已经完成的 disclosure route 与
> reciprocal probe，并把自造 event/probe ID 当成冻结证据。

scorer 因而返回：

- `RECIPROCAL_PROBE_MISSING`；
- 两个 `REQUIRED_DISCLOSURE_PATH_MISSING`；
- 多个 `UNKNOWN_EVIDENCE`。

这不是格式小错。它说明语义匹配、policy 和 holder authorization 即使全部存在，也不能替代
真实执行和权威 receipt。

## 被及时撤回的第二次错误

truth/controller owner 一度手写了三份 schema 合法的“completion receipt”，随后复核发现：

- 冻结材料只有 declarative `available_actions`、route/policy 条件和 witness 名称；
- 仓库中没有可调用 route/onward/reciprocal executor；
- 没有权威 receipt issuer、状态机或既有执行日志；
- `PROPOSE_RECIPROCAL_PROBE` 不是 completion action；
- ION 的 `derived_receipt_required` 不是已经存在的 derived receipt。

这三份无权威 completion JSON 已撤回并删除；`candidate-controller/` 为空。没有 V2 分数。
`build-candidate-v2.py` 只保留为 blocked design sketch，在权威 receipt 不存在时明确退出
`BLOCKED_BY_MISSING_CONTROLLER`。

## 研究含义

现有技术已经完成：

- 本地触发和最小投影；
- task-relative compatibility；
- direction/version/epistemic state；
- disclosure policy 与 onward 条件；
- opportunity routing 的语义判断。

尚未完成的不是“再做一个搜索目录”，而是：

> 一个能在相互独立 Authority 下实际执行 disclosure route / reciprocal exchange、维护
> idempotency 与版本状态、并签发可被 scorer 和 relation handoff 验证的 controller。

下一步不能继续手写 receipt。必须先冻结并实现 controller executor、state transition、
receipt issuer 与 failure/replay contract，再在新的留出世界上检验；在 HW-B 上修补后的分数
只能作为 development result，不能冒充第二次盲测。

## Wave 004 development follow-up

Wave-004-A 已实现受信本地 controller，Wave-004-B 把 HELIOS、ION、JUNIPER、KITE 四份
原始 holder receipt 的 byte hash 冻结进 normalization contract，并真实执行：

- HELIOS direct；
- ION direct + derived onward；
- JUNIPER/KITE counterparty exchange。

所有 route 都先写 recipient store、再从磁盘 readback、最后签发 execution receipt。四个独立
攻击（changed contract replay、changed contract pending recovery、tampered audit outcome、
deleted recipient store）均被拒绝且零写。

第一次 controller-derived V2 仍只得 `4/8 = 0.50`。运行后检查发现 method-visible schema
没有公开 depth 单位、reciprocal requester/responder 方向和 terminal status 枚举，而 scorer
对三者采用隐藏精确约定。保持所有实质 route 不变，只在 post-oracle V3 映射这三项表示后，
scorer 得到 `8/8 = 1.00`。

该结果不是新的 blind evidence。它区分出：

- `1/8 → 4/8`：从手写伪执行转为真实 controller execution；
- `4/8 → 8/8`：隐藏 evaluator 表示约定，不是新增解决机制；
- 仍未解决：真实 holder 签名、relay/recipient 独立 ACK、外部 append-only anchor 与跨权限域
  故障试验。

具体证据见 `runs/wave-003-a-held-out-world/g1/t1-hw-b/EVALUATOR-SEMANTICS-DEFECT.md`。
