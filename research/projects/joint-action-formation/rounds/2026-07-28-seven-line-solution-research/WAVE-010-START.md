# Wave 010 — 从 Pro 候选到自有问题的可执行闭环

日期：2026-07-29  
状态：`STARTED / DESIGN REPAIR ACTIVE / FIRST FREEZE BUNDLE NOT YET ACCEPTED`

## 本轮目标

Wave 010 不以证明通爻独占、特殊或必须新增机制为目标。它要在同一个冻结任务上回答：

> 强中心、成熟组件组合、平台直达、人工协作或其他方法，究竟能否从协调接口内的 Intent
> 开始，形成具备当前权威的前半程候选，并在未来能力、权限、资源、执行、接受和依赖变化下
> 完成可验证的 episode closure？

现有方案完整解决、并列或更便宜，都是正向结果。只有在同等 lawful input、Authority、
预算、恢复与全生命周期成本下，多个强基线仍留下同一个稳定、可复现、因果承重的缺口时，
才讨论新的有界机制。

## 为什么不直接运行 Pro 提出的 66/72

两个 Pro 返回提供了有价值的问题重建、baseline families、paired motifs 和失败攻击，但它们
没有读取本地 Wave 009 的完整返回，也没有冻结 truth population。独立审计确认：

- X1 的 20/60/6 与 X2 的 64+8/72 只能作为设计或运行预算草案，不是真值分母；
- X1→X2 原设计会丢失 `BOUNDED_UNREACHABLE`、`SAFE_EXIT` 和精确 G5 reason；
- X1 十组 motif 中，多数 primitive delta 会因果传播到多条线，不能伪称其他 line truth
  全部相同；
- X2 仍可能让一个 mega-owner 代签五层 postcondition truth。

因此本轮先修复状态代数、配对正交性和 truth-owner 边界，再创建最小冻结对象。修复不是
形式合规：任何一处失真都会让后续方法比较的分母、失败归因或“问题已解决”判断失效。

## 七线如何进入同一轮

七条母线保持各自 truth、证据和失败边界：

- X1：G1 discovery handoff、G2 relation semantics、G3 causal reachability、G5 current
  authority，共同产出 `AUTHORITY_VALID_FRONT_HALF_CANDIDATE` 或无损 typed non-success；
- X2：G4 prospective reliance、G5 execution-time authority、G6
  Attempt/Effect/Adoption/Acceptance/Settlement 分域 readback、G7 affected reopen；
- T5：平台直达、轻 adapter 与完整 relation formation 的 collapse gate，始终单列。

G5 在 X1 与 X2 出现于两个不同时间点：X1 只判断 handoff eligibility，X2 在实际 attempt
紧前重新判断 execution authority。前者不能预签后者。

## 已冻结的设计边界

1. 唯一 `V0` 保留 V1 的原始价值与不可接受底线；`BE0` 只表示公平实验能力边界。
2. 唯一 episode-level qualification 是 `Q_episode`；各线只拥有 `A_Gi` 与 typed
   transition contracts。
3. X1 从 `INTENT_AT_COORDINATION_INTERFACE` 开始；pre-Intent generation 不计入 V1/V2。
4. X1 outcome 使用
   [`WAVE-010-X1-OUTCOME-CONTRACT-v0.json`](./WAVE-010-X1-OUTCOME-CONTRACT-v0.json)，
   无损保存 category、registered reason、四线 receipts 和四个 transition receipts。
5. X2 必须机械接收每个 arm 自己的全部 finalized X1 outputs；不得手写成功 relation、
   删除 non-success 或共享 canonical success。
6. baseline 完全获胜、candidate 无增量、合法拒绝、Unknown、safe exit 和不可发现，均为
   必须保存的结果。

## 第一可执行对象：M01 freeze bundle

当前不实现 world factory、solver 或 runner。第一对象是
`X1PairedEpisodeFreezeBundle-v0` 的 M01 一对：

- 两个新鲜 opaque episode anchors；
- 完全相同的 Intent、`V0`、`BE0`、`Q_episode`、action grammar、bound 与 horizon；
- 唯一 primitive delta：当前 directory 是否已经拥有一个 lawful projection；
- local purpose-bound projection path 在两侧都存在并合法；
- G2/G3/G5 private fragment 必须逐字等同；
- G1 的 `BearingDeltaCertificate` 明确 changed bytes/event、可见差异、affected-line set、
  propagation/scoring mask 和 non-bearing equality proofs；
- 四个 owner 分别给出 private fragment commitment、key id 与 ledger root；
- public packet 不得出现 motif、A/B、expected outcome 或 base-family label。

该 bundle 只证明一个 scoreable pair 有资格成为未来分母候选，不证明任何方法已解决 X1。
未经不同研究者的正交性、信息泄漏和 owner-collapse 审查接受，不进入 solver/runner 阶段。

## 接下来的门

1. 修完 X1/X2 设计与 canonical outcome 合同；
2. 由不同 owner 形成 M01 四份 truth fragment 和公共 packet；
3. 组装、重算 exact bytes/hash，并完成独立只读审查；
4. 审查通过后，才分别实现强中心、成熟组合、人工接口和候选 arm；
5. 先跑 leakage、transplant、unequal-access 与 fail-closed attacks，再启用 score；
6. X1 实际 finalized outputs 出现后，才机械形成 X2 population。

本文件启动 Wave 010，但不宣称 M01 已冻结、X1/X2 已运行、任何方案已有覆盖率，亦不改变
Problem、MechanismProfile 或 NAC 的正式状态。
