# Wave 004 cross-line implications

日期：2026-07-28  
来源：HW-B V1/V2/V3、Wave-004-A controller、Wave-004-B integration  
状态：`NEXT-EXPERIMENT ROUTING / NOT STABLE CLAIMS`

## 共同发现

Wave 004 证明了一个组合链在本地合成条件下可以工作：

`local trigger/projection → compatibility/policy → holder authorization → controller execution
→ recipient readback → candidate handoff`

它同时证明这条链不能被压成一个“已形成关系”的总状态。每一段有不同的 authority、证据、
失败和复用边界。scorer 的表示契约也不是外层格式问题；如果未公开语义决定了 pass/fail，
它会改变方法可达性，必须作为任务环境的一部分冻结。

## G2 — Relation from task

- 可复用能力：task-relative projection、方向/兼容键、controller execution receipt、无承诺
  handoff。
- 当前缺口：双方收到信息不等于双方理解、认领关系范围，也不等于 commitment。
- 下一实验：对同一任务比较三组：
  1. 只有 semantic match；
  2. match + 双 recipient ACK；
  3. match + ACK + 双方 explain-back + version-bound relation proposal。
  测 relation false constitution、澄清次数、撤回后残留状态与后续任务复用。
- 最强反例：双方完成 reciprocal disclosure，但其中一方把它理解为一次性检索，不认领持续
  关系。
- 结果影响：若第 2 组已完整满足后续任务，则 RelationVersion 只保留为派生记录；若第 3 组
  显著减少错误复用，才支持独立物化。

## G3 — Form reachability

- 可复用能力：显式 condition/policy、受限 disclosure、typed epistemic state、可执行
  controller。
- 当前缺口：controller 能执行已授权路径，不会创造缺失的权限、意愿、资源或可理解表示。
- 下一实验：冻结同一初始任务，分别缺少表示、工具、权限、伙伴或恢复条件；允许系统只增加
  一类条件，观察哪些原本不可达状态变为可执行并被 ACK。
- 最强反例：模型生成一个逻辑完整的新路径，但承担风险的主体拒绝，reachable 仍为 false。
- 结果影响：只把被实际 condition change + postcondition 区分的算子保留为 formation；
  纯改写提示或隐藏 evaluator label 不计。

## G4 — Capability to reliance

- 可复用能力：单次 execution receipt、recipient readback、idempotency、revocation/version。
- 当前缺口：一次成功 operation 不支持稳定 capability，更不支持 Principal 可以依赖它。
- 下一实验：同一 frozen operation 经状态漂移、credential rotation、延迟、部分故障和恢复
  重放，比较“声明能力”“最近 probe”“连续 receipt history”“带 SLA/恢复责任”的校准误差。
- 最强反例：probe 成功后 credential 立即撤销，系统仍把 capability 交给关系构成。
- 结果影响：若最近 probe 已足够校准低风险任务，则直接采用；只有 history/责任结构在相同
  成本下显著降低错误依赖，才保留更强 Reliance 对象。

## G5 — Authority composition

- 可复用能力：policy snapshot、holder authorization hash、controller contract、recipient
  readback。
- 当前缺口：Wave 004 的 controller 可以代表 relay 写第二跳，但没有 relay 的签名 delegation
  或 ACK；同进程自读回不能证明跨 Authority 行动。
- 下一实验：把 holder、controller、relay、recipient 分成不同 signing domain；derived
  onward 必须绑定 relay-signed authorization，reciprocal 必须绑定两侧 ACK；同任务比较
  trusted central controller 与分域链的覆盖、延迟、失败和伪造面。
- 最强反例：controller 合法持有源 holder policy，却伪称 relay 已转发。
- 结果影响：若强中心在明确 delegation 下完整解决，则中心方案进入通爻；若无法获得或验证
  delegation，只研究该有界差异，不新造全局 Mandate 体系。

## G6 — Effect that counts

- 可复用能力：authoritative delivery event、recipient store postcondition、readback receipt。
- 当前缺口：信息已送达是 delivery-level Effect，不是业务任务完成、Adoption、Acceptance 或
  Settlement。
- 下一实验：为同一实际任务建立 effect ladder：
  `attempt → delivery → recipient ACK → domain postcondition → beneficiary acceptance`，
  对每级做“上一级伪造下一级”的 mutation。
- 最强反例：recipient ACK 了消息，但领域资源从未改变，系统却结算业务完成。
- 结果影响：保留最小能阻止 false promotion 的 Authority Gate；已有 workflow/event-sourcing
  能完整表达时直接采用。

## G7 — Reuse and safe reopen

- 可复用能力：request hash、contract-state binding、audit chain、exact replay、revocation。
- 当前缺口：本地 hash chain 不抗同目录恶意改写；key/schema/authority 变化后的迁移和 reopen
  仍未检验。
- 下一实验：在已完成 route 后注入 contract change、key rotation、recipient withdrawal、
  anchor fork、schema alias 与 partial recovery；比较 immutable replay、migration adapter
  与重新授权三种策略。
- 最强反例：旧 receipt 在新 contract 下被 replay，并签出绑定新 contract 的成功证明。
- 结果影响：Wave 004 已否定这种 replay；下一轮决定哪些变化可无损迁移，哪些必须 reopen，
  而不是把所有 drift 统一当失败或统一自动迁移。

## 调度含义

Wave 005 优先 G5/G6/G7 的分域 receipt kernel，同时由新的 HW-C 检验 G1 的公开表示契约。
随后把同一分域证据喂给 G2/G3/G4；这样每条线共享实际任务和底层 event，却仍分别检验关系、
条件形成和可靠依赖，避免一个局部 PASS 晋升整条体系。
