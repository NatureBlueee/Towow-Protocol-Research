# Wave 007 repair harness

日期：2026-07-29  
状态：`STARTED`

共享任务继续使用：

- `W6-STERILE-ROUTE-SIMULATION-001`
- shared-task SHA-256：
  `0cde980b1cd9754d61e1cc2f9478a85c9f587ec5fb5b4e7c07ccb068fbc100a3`

Wave 007 不修改任务价值、operation、主体、authority 边界或 E0–E8 时序，只修复 Wave 006
攻击暴露的被测接口和 evaluator。

## 共同禁止项

任何候选策略均不得：

- 读取 semantic `case_id`、expected outcome、`valid_current_possible` 或 evaluator truth；
- 持有另一个 authority domain 的 private key；
- 自报 false positive、false negative、promotion、accepted 或 net value；
- 用 strategy label 决定成本；
- 通过删改拒绝、撤销、缺失或 UNKNOWN 来提高分数；
- 从同一模块同时获得 world truth、签名生成与评估结果。

Evaluator 必须：

- 从独立 truth、签名验证、postcondition 与 operation log 重建结果；
- 对候选不可见的 paired worlds 分别计分；
- 把 `UNKNOWN / REFUSE / ABSENT` 保持为不同 observation；
- 对证据读取、验证、authority request、重试、披露和恢复按实际日志计费；
- 运行 rename、evidence deletion、label/function swap、truth-label flip 与 unauthorized-signature
  mutations；
- quorum 只按 contract allowlist 中绑定同一 checkpoint/slot 的 unique issuer 计票，并攻击
  duplicate、replayed 与 cross-checkpoint attestation；
- 报告每项 scoped claim 的支持、反驳或 Unknown，不输出一个整体好/坏等级。

## 007-A：G6/G7 opaque authority harness

优先级：第一。

最小 paired worlds：

- holder active / holder revoked；
- recipient active / recipient withdrawn；
- beneficiary accepts / beneficiary refuses；
- exact replay / material command change；
- schema alias / semantic drift；
- healthy anchor / equivocated anchor。

策略只可向独立 Authority service 请求签名或 refusal。Authority service 根据自己的 private
state 决定，candidate 看不到该 state；所有返回绑定 exact bytes、purpose、operation、key、
environment 与 sequence。

成功标准不是“全部恢复”，而是：

- valid world 能完成到相应 effect level；
- revoked/refused world 不被伪装成 valid；
- exact replay 不重复制造现实 effect；
- material drift 不借 adapter 绕过 re-authorization；
- refusal、UNKNOWN 和 ABSENT 留下可重建的不同结果；
- 成本来自实际调用和证据日志。

## 007-B：G2 paired relation materiality

至少构造两组 candidate 不可见的 paired worlds：

1. `ONE_OPERATION_ONLY` 与 `EXPLICIT_BOUNDED_REUSE_AUTHORIZED`；
2. relation evidence valid 与 relation evidence missing/contradictory。

三类 representation 必须实际改变候选可见 evidence，而不是只改变名称和成本。Evaluator
从 delivery、ACK、explain-back、proposal、authorization、withdrawal 和 reuse trace 重建：

- false constitution；
- missed legitimate reuse；
- stale reuse；
- withdrawal residual；
- evidence/disclosure/coordination cost。

若 task-bound evidence 在 one-shot world 足够，这是正向结果；若 bounded reuse world 需要
更强 relation evidence，也应精确指出增加的是哪项可观察能力。

## 007-C：G4 access-metered reliance

每个 strategy 通过同一 evidence API 获取信息。API 记录：

- 读取了哪些 declaration、probe、receipt、health、SLA、recovery receipt；
- 是否验证 signature、binding、freshness 与 authority；
- 请求次数、bytes、延迟、失败和重试；
- 当证据缺失或冲突时返回的 observation。

成本只由 operation log 计算。结果同时报告：

- per-scenario confusion/cost/recovery；
- distribution shift；
- failure-loss 与 evidence-cost sensitivity；
- Pareto frontier；
- 被其他策略支配的 region 与无结论 region。

不得把单一聚合 winner 写成普遍推荐。

## 当前调度

- 独立攻击者转为构建并攻击 007-A；
- 成本敏感性研究者构建 007-C；
- cross-authority/relation 研究者构建 007-B，主研究者负责跨线不变量与独立 mutation；
- anchor-equivocation 首轮已被 duplicate-vote mutation 缩窄，其修正条件作为 007-A 的
  healthy/equivocated paired world 输入；
- HW-C 外部 blind extraction 仍保持 `0/11 NOT_STARTED`，不因本轮本地工作绕过精确外发授权。
