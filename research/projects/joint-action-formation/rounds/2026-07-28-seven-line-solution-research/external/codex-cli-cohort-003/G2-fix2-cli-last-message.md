G2 第三轮已完成，并通过独立攻击复核。

- A 复现旧 verifier 接受 wrong-kind、wrong operation/schema/ordinal/time。
- B 实现完整 request/receipt、freshness、constitution 与 trust 绑定。
- C 独立发现 `PRIVATE_COLUMN_UNKNOWN` provenance 红灯；根会话最小修复后原测试转绿。
- 最终测试：`67/67 PASS`。
- 双跑：每轮 7 场景，256 signed receipts，62/62 unique PID/key，784 trace，语义一致。
- 全 Unknown 仅生成 `DERIVED_CANDIDATE_WITH_UNRESOLVED_CONSTITUTION`，无 `AUTHORIZE/ACTIVATE`。
- T5 仅为 `LOCAL_FIXTURE_SELF_ASSERTION_VERIFIED`。
- 真实 PKI、owner/platform identity、G5/G6、Effect、Acceptance、Settlement、完整 CE-001 均保持 `NOT_RUN/NOT_ESTABLISHED`。

交付记录：[G2-fix2-final.md](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/external/codex-cli-cohort-003/G2-fix2-final.md)

独立攻击记录：[C-FIX2-ATTACK.md](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-012-ce001-power-restoration/g2-relation/C-FIX2-ATTACK.md)

写入严格限定在 `g2-relation/` 与 `G2-fix2-final.md`。