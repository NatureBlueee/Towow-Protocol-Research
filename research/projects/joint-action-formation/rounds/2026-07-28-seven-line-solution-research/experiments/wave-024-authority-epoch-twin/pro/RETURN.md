# W024 Pro 独立返回凭据与本地结构化捕获

日期：2026-08-01  
状态：`EXTERNAL CLEAN-ROOM CANDIDATE / LOCAL ACCEPTANCE PENDING`

## Provenance

- task ID：`W024-PRO-CLEANROOM-AUTHORITY-RECOVERY-001`
- task packet：`TASK.md`
- task packet SHA-256：`3ecf74e7c611e66ed6ef1566d39f57bc579b5846a39675728c43c8ead8ca351b`
- 会话：<https://chatgpt.com/c/6a6d7b4a-a178-83ea-80d4-57972964482f>
- 页面标题：`Clean-room研究输出`
- 页面显示推理档位：`极高`
- 页面显示思考时长：`6m 16s`
- 可见 main 文本长度：`17,683` 字符
- 可见 main 文本 SHA-256：`d3d674afd99953861830b629ee58eee5eaaecd5dd96ca5694db53469bf110240`

没有取得精确 provider model identity、request/response byte receipt 或 usage receipt，因此本返回
不是 Wave 021/023 的正式 A3 treatment，也不是独立现实证据。TASK 只披露有界问题、成熟组件
候选、已知失败和返回边界；未披露本地 Wave 024 QUESTION、红队、迁移矩阵或实现选择。

## 它独立重建出的核心问题

Pro 没有把问题归结为 workflow 是否 green、credential 启动时有效、最终状态等于目标、签名/
hash/manifest 完整或 controller 能否恢复。它把承重点重建为：

```text
Authority revocation 与 Target Effect commit
是否存在一个可验证的共同线性化顺序。
```

它指出：即使在线 introspection 完全禁用缓存，只要 `active=true` 检查与 Effect commit 是两个
可分离事件，就仍存在 `check → revoke → commit` 的最后一跳 TOCTOU。这个判断与本地红队的
`owner revoke → Target durable fence ACK → request ingress/linearization` 独立收敛，但模型共识
本身不升格为证据。

## 最强现成方案与替代方案

Pro 的首选不是新协议，而是：

```text
Target-side atomic guard-and-commit
+ durable operation/effect ledger
+ owner-native Acceptance/finality
```

统一合法域内可以由 serializable transaction、operation/request digest 唯一约束、Target-local
current Authority head/fence、Effect/receipt 原子写入直接闭合。ACK 丢失后用同一 operation ID
返回原 terminal receipt；不同 request digest 冲突；不能让 controller 创建新成功记录。

Authority 与 Target 真正分域时，Pro 给出三种诚实选择：

1. 让 revoke 与 commit 进入同一个共享 transaction/consensus/sequencer；
2. 将范围、对象、版本和次数均受限的一次性 commit right 委托给 Target，使 consume/cancel 在
   同一原生账本竞争；
3. 明确改成 lease/fence 语义：已签发 lease 在期限内不可即时撤销。此时解决的是“lease 在
   commit 时有效”，不能继续宣称 external Authority head 当时仍 current。

`online introspection + Target idempotency` 只解决 recovery/exactly-once，不解决最后一跳竞态；
durable workflow、消息 exactly-once、LLM/controller 或人工协调也不能绕过 Target/Authority
truth owner。

## 建议的最高信息量 discriminator

它把下一本地测试从普通 S/R world 进一步 sharpen 为：

```text
POST-CHECK / PRE-COMMIT REVOCATION CUT

authority check returns current
             ↓ deterministic barrier
owner revoke + native receipt
             ↓ release Target
Target attempts Effect commit
```

这一区分三种仍可能存活的解释：

- 真正共享线性化边界：只允许 commit-first=一次 Effect 或 revoke-first=零 Effect；
- lease/delegation：可能安全，但必须重写命题；
- last introspection + idempotency：能处理 ACK loss，却会在该 cut 暴露 TOCTOU。

它还要求 commit/reject 后都对称丢失首个 ACK、终止 candidate，并从 Target-native status/readback
恢复；S 恰好一次 Effect + owner-native final acceptance，R 零 Effect + owner-native
`FINAL_REJECTED_NO_EFFECT`，controller report 不参与 verdict。

## 对公平比较的归因校正

外部 TASK 没有披露 A1–A5/C1–C3 的本地语义，因此 Pro 正确地把编号视为 opaque arms，而没有
擅自扩写。这是 clean-room 边界成立的正例；具体迁移由本地 `TRANSFER-MATRIX.md` 负责。

它提出必须区分三类“赢家”：

- `Platform/owner API winner`：atomic fence/dedupe/readback 已由公共底层完成；
- `Composition winner`：较低级原语由某成熟组合正确拼成完整闭环；
- `Coordinator winner`：底层保证相同，只在恢复、成本、可用性或人工负担上不同。

如果 A1–A5 都调用同一个已经完成 currentness、dedupe、readback、Acceptance 的 API，正向结论
是“公共成熟平台解决 residual”。不能把同一底层保证重复计作模型、人工、workflow 各自的
独立成功；需要 attribution 与 ablation。

## 本地采用与拒绝边界

采用：

- 把 post-check/pre-commit cut 加入 Wave 024 最小判别设计；
- 把 strict currentness、one-shot delegated right 与 lease semantics 分型；
- 把 platform/composition/coordinator 的贡献归因写入后续公平 batch；
- 用实际本地 runner 与原生 receipts 检验，而不是引用本返回作为答案。

不采用或尚未核验：

- 页面引用的 RFC、PostgreSQL、Temporal、AWS、Stripe、Kafka、Zanzibar 等 source families 尚未
  在本地逐项读取权威原文，不以本文件作为正式引用；
- 外部建议没有访问本地 runner、DB、测试或 artifact，不能证明实现存在或门已经关闭；
- 外部 task 未给出 A1–A5/C1–C3 语义，所以其迁移建议不替代本地具体矩阵；
- 不把本地 synthetic key 称为现实 lawful Authority，不把 Pro 返回称为真实 treatment。

```text
external_problem_reconstruction = USEFUL_CANDIDATE
independent_convergence = OBSERVED_NOT_EVIDENCE
best_existing_solution_candidate = TARGET_ATOMIC_GUARD_COMMIT_LEDGER_OWNER_FINALIZATION
next_discriminator = POST_CHECK_PRE_COMMIT_REVOCATION_CUT
formal_A3_treatment = NOT_RUN
local_runtime_result = PENDING
comparative_result = NONE
winner = NONE
```
