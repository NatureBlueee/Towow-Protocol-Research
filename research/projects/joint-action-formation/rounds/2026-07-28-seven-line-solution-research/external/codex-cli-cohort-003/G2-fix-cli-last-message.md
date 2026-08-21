G2 CE-001 根红灯已修复，并完成 A/B/C 独立复核。

关键结果：

- 五个 owner 由独立 subprocess/state/key 返回签名 act。
- Receipt 使用 Ed25519 签署 exact raw bytes，绑定 owner、episode、Q、object、purpose、revision、time 与 decision。
- controller 不读取完整 owner profiles，并强制 PID、process instance、key 与 public key 跨 owner 唯一。
- C 发现的 identity-collision 红灯已修复并原样复跑通过。
- T5 改为 platform-native 签名 proof + readback，不再接受裸布尔。
- Unknown、refusal、blocking/nonblocking opposition 均保持。
- `authorized/activated` 仍为 G5/G6 未验证，无绿色总状态。

最终验证：

- 合并测试：`46/46 PASS`
- 双跑：`2 × 6` 场景
- `250` 份签名 receipt
- `52` 个 process instance、unique PID 和 unique key
- `52/52` 子进程正常退出
- `764` 条 raw trace
- `semantic_rerun_equal=true`
- source manifest 与当前实现匹配

交付：

- [G2-fix-final.md](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/external/codex-cli-cohort-003/G2-fix-final.md)
- [g2_relation.py](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-012-ce001-power-restoration/g2-relation/g2_relation.py)
- [C-FIX-ATTACK.md](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-012-ce001-power-restoration/g2-relation/C-FIX-ATTACK.md)
- [summary.json](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-012-ce001-power-restoration/g2-relation/outputs/summary.json)
- [process-source-manifest.json](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-012-ce001-power-restoration/g2-relation/outputs/process-source-manifest.json)

只修改了获准的 `g2-relation/` 和 `G2-fix-final.md`。真实 owner、法律充分性、Effect、Acceptance 与完整 CE-001 均保持 `NOT_RUN`。