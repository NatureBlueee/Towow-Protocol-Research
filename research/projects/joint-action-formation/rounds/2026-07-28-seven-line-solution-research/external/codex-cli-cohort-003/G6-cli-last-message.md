G6 已完成，只新增指定 `g6-effect/` 与 `G6-final.md`。

结果：

- 全套测试：`41/41 PASS`
- 敌对攻击：`20/20 PASS`
- Semantic conformance：`6/6`
- Failure injection：`4/4`
- Local synthetic E2E：`8/8 CorrectResolution`
- ExactTaskSuccess：`6/8`
- 真实产品、生产 Effect、真人 Acceptance、付款 finality：均 `NOT_RUN`

E3B 的错目标损害、恢复和后续成功均保留，未被改写成 ExactTaskSuccess；恢复必须经过独立 target-state readback。

交付：

- [G6-final.md](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/external/codex-cli-cohort-003/G6-final.md)
- [模块说明](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-012-ce001-power-restoration/g6-effect/README.md)
- [敌对审查与红灯历史](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-012-ce001-power-restoration/g6-effect/ATTACK.md)

未修改 contract、NOW、PROGRAM、Problem、LineContract 或机制状态。