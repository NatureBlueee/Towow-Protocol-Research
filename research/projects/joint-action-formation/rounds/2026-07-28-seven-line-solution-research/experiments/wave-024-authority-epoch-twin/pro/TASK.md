# W024 Pro clean-room task

Task ID: `W024-PRO-CLEANROOM-AUTHORITY-RECOVERY-001`  
Packet version: `v1`

## Question

在一个真实执行过程可能“提交成功但 ACK 丢失并崩溃”，同时授权也可能在提交前被撤销的任务中，
怎样用最小但有区分力的本地实验判断：执行者是否在 **commit-time current Authority** 下只产生
一次 exact Target Effect，并在恢复后由 owner-native Acceptance 与 finality 完成；而不是由
controller、静态 credential、最终状态或自报字段事后拼出成功？

这来自 Towow Problem V1/V2 的一个有界 residual：对象、Target、Authority、Effect、readback、
Acceptance 和恢复必须在同一任务谱系内成立。现有强中心、平台、通用模型、成熟组合、人工制度
或 adapter 只要可复现地解决，就是正向答案；不要求 Towow 独占技术。

## Why it matters

上一轮只证明静态 manifest 可以阻止若干假绿，并明确拒绝实际比较；它没有运行 candidate，
没有证明 lawful Authority、Effect、Acceptance，也没有产生比较赢家。下一步需要选择一个真正
能够区分竞争解释的实验，而不是继续增加 schema 或同质 case。

## Evidence you may use

- 既有成熟组件候选：durable operation ledger、one-shot capability、signed status/readback、
  persistent epoch fence、owner head revalidation、append-only Acceptance/finality。
- 已知失败模式：静态 credential 在 commit 前已撤销；Effect 已发生但 ACK 丢失；crash 后重复
  execute；controller 代写 owner truth；最终状态相同但 actor/Authority 不同；fixture 自带 key
  冒充 lawful Authority；撤销或故障标签泄漏给 candidate。
- 当前没有可信现实 Principal registry、生产系统或真人资源。本地实验只能支持高保真合成范围。

## Current known state

- Supported: manifest 层可以封闭部分 source/Q/candidate/launch/meter/trigger 攻击，并 hard-reject
  actual-comparison 声明。
- Failed or contradicted: 字段/profile/hash 形式完整本身不能证明运行 preimage、当前 Authority、
  native Effect 或 Acceptance。
- Unknown: 最小实验应如何划分独立域、怎样形成同形 blind worlds、哪些 receipt 足以区分
  commit-current 与 pre-commit-revoked、哪些成熟方案能直接解决、结果如何迁移到 A1–A5 比较。

## Required result

从零重建问题，提出最强现有/组合解决方案及竞争方案；设计一个最高信息量的本地实验与最强反例。
不要默认 S/R twin 或任何已有组件划分必然正确。如果更简单实验更有区分力，请替换它。

## Success means

- 实验能区分“current Authority 下 exactly-once Effect 后恢复完成”与“撤销后零 Effect”，且差异
  不是由 case label、ID、顺序、格式或 controller oracle 泄漏造成。
- 清楚指出每项事实应由哪个独立原生域产生，哪个攻击会推翻结论，以及结果对 A1–A5 公平比较
  能说明什么、不能说明什么。

## Hard boundaries

- Do not assume access to local files, tools, tests, or unlisted history.
- Do not report proposed or authorized action as executed.
- Do not invent measurements, citations, or external acceptance.
- Existing, central, general-model, human, adapter, or combined solutions count as success when they solve the question.
- 不以证明 Towow 特别、不可替代或需要新协议为目标。
- 不把本地签名 key 等同于现实合法 Authority，不把同一模型的赞同当独立证据。

## Return

1. Problem reconstruction.
2. Best solution and strongest alternatives.
3. Minimal experiment, independent domains and exact observable outcomes.
4. Strongest counterexamples and falsifiers.
5. What the result transfers to A1–A5/C1–C3, and what remains untested.
6. The next local test that best distinguishes the surviving explanations.
