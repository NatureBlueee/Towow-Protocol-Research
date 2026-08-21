# Wave 007 seven-line routing

日期：2026-07-29  
状态：`PRE_RESULT_SCOPE_MAP`

Wave 007 的三个实现直接检验 G2、G4、G6、G7，但其修复条件同时约束 G1、G3、G5。这里预先
冻结跨线谱系，防止某一条实现 PASS 后无界晋升七线。

| 目标 | Wave 007 实际观察 | 允许改变的判断 | 不允许推断 |
|---|---|---|---|
| G1 Discovery before search | candidate-visible packet 是否含有采取下一步所必需的 authorization/evidence projection；删证据后是否仍伪通过 | 哪些最小显式信息是本任务可发现/可行动的必要条件 | 未表达机会的一般发现率；HW-C 11 packet blind score |
| G2 Relation from task | one-shot/bounded-reuse paired worlds；valid/missing/contradictory relation evidence | 哪类 evidence 对继续关系或 legitimate reuse 有材料性 | 真人共同认领；长期 relation ecology 价值 |
| G3 Form reachability | revoked/refused world 是否能经合法 re-authorization 获得新可达路径；valid world 是否原本已有等价路径 | 某个 operator 是否创造了此前不存在且获权的局部路径，或仅发现/恢复旧路径 | 从合成签名路径推出一般新能力形成 |
| G4 Capability to reliance | 同一 evidence API、实际访问/验证成本、paired drift 与 distribution shift | 哪类当前证据在何种损失/成本条件下足以支持 reliance | 单次 operation success 自动成为 capability 或 business effect |
| G5 Authority composition | 独立 Authority service 的 request/refusal、key isolation、bytes binding、unique witness | 现有签名、ACL/policy、workflow、quorum 组合是否已覆盖本地 authority gate；还剩什么 adapter 差异 | controller 替主体签名；合成 policy 等于真人授权 |
| G6 Effect that counts | 五级 authority/postcondition 分离；revoked/refused/partial paired worlds | 哪一级 effect 由哪些独立证据支持，哪些漂亮上游事件不能晋升 | L3 推出 beneficiary acceptance；本地签名推出现实效力 |
| G7 Reuse and safe reopen | exact/material、alias/drift、healthy/equivocated、replay/reauthorize | 何种变化可 replay、migrate、defer 或必须重新授权 | 一次恢复策略普遍适合所有 drift |

## 结果路由规则

1. 007-A PASS 最多支持 G5/G6/G7 的本地合成 scoped claims；只有出现新授权路径且排除原有等价
   路径时，才给 G3 formation 提供候选证据。
2. 007-B PASS 只改变 G2；其 evidence projection 对 G1 只是必要信息条件，不是 discovery
   方法有效性证据。
3. 007-C PASS 只改变 G4；SLA、probe、receipt 或 declaration 胜出都不晋升 Effect。
4. 现有中心 workflow、签名、policy service、gossip 或 quorum 完整覆盖受检验 scope 时，直接
   记录为通爻方案的正向组成；不再额外制造同能力协议对象。
5. 现有组合若依赖单维护者、特定格式、集中 trust root、不可移植 API 或不满足作用域要求，
   分别登记依赖/格式/trust/迁移残余，不因“现成”而豁免攻击。
6. G1 HW-C exact external blind extraction 在获得精确 provider/payload 授权前仍为 `0/11`；
   Wave 007 不冒充该盲测。

