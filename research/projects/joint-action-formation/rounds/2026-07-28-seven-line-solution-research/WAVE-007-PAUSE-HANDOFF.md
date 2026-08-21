# Wave 007 pause handoff

日期：2026-07-29  
状态：`PAUSED_AT_USER_REQUEST / RECOVERABLE`

## 本轮真正完成了什么

Wave 006 的 45/45 绿灯被独立攻击推翻或缩窄；Wave 007 的 A/B/C v1 又分别暴露：

- L4 正确终态掩盖 L3 重复 effect；
- callable closure 泄漏 truth/log，确定性 signer 可重建；
- candidate 可清空同进程计费日志、重放旧 ACTIVE authority receipt、自报实现身份。

这些失败均原样保留。A2/B2/C2 在新目录修复，root 收尾复跑：

- A2：17/17 PASS；
- B2：20/20 PASS；
- C2：15/15 PASS；
- 合计：52/52 PASS。

当前支持只到 `LOCAL_SYNTHETIC / ROOT_RECHECKED`，不是 blind、独立实现、现实或生产证据。

## 当前最佳方案

本轮没有发现必须创造新协议机制的证据。当前有界问题由现有技术组合解决：

- parent-side broker/process boundary；
- runtime-random Ed25519 authority keys；
- exact bytes、purpose、operation、environment、authority head/epoch binding；
- attempt-time idempotency；
- domain postcondition（L3）与 beneficiary acceptance（L4）分离；
- unique allowlisted witness quorum；
- runner-owned implementation identity；
- 从 parent operation log 重建成本；
- paired hidden worlds、truth-only evaluator 与 mutation。

这本身是通爻正向成果：价值在于把成熟能力按 V1/V2 问题条件正确串联、限定和复现，而不是
强求独占技术。

## 恢复入口

1. `research/NOW.md`
2. `WAVE-006-AUDIT-INVALIDATION.md`
3. `WAVE-007-AUDIT-STATUS.md`
4. `WAVE-007-INDEPENDENT-AUDIT-PROTOCOL.md`
5. `audits/wave-007/root_attack_a.py`
6. `audits/wave-007/root_attack_b.py`
7. `experiments/wave-007-a2-opaque-authority-harness/`
8. `experiments/wave-007-b2-paired-relation-materiality/`
9. `experiments/wave-007-c2-access-metered-reliance/`

## 暂停后仍未解决

- HW-C exact external blind extraction：`0/11`，仍需精确 provider/payload 授权；
- 同权限 hostile code 的 filesystem sandbox；
- malicious anchor 的真实 cross-view equivocation，而非 central detector fixture；
- 新 blind holdout、独立实现复核与现实任务；
- G1/G3/G5 与本轮结果的下一批独立任务验证。

用户已要求等待额度恢复。本轮不启动 Wave 008，不调用外部研究模型，不发送 HW-C packet。

