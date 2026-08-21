已完成第二批 G6 独立 CLI 研究与实现。

核心结果：

- 实际并行使用三名内部研究者 A/B/C，分别完成语义、runner、对抗门禁。
- 12 pairs、24 worlds、3 Authority strata、3 独立 executables，共 108 records、216 次 worker 执行。
- 五道失效门全部通过：
  - truth-copy
  - method-alias
  - wrong-object：9/9
  - read-skew：9/9
  - unauthorized real Effect：12/12
- 31/31 tests PASS；private oracle 有限检查 108/108 PASS。
- S1 统一权威与 S3 精确合法委托中的中心闭合是正结果；S2 中越权中心代行被正确阻断。
- 成熟 composition 与 human institution 同样完整通过当前有限分母；未观察到需要新 Effect protocol 的 residual。

交付入口：

- [README.md](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-011-g6-role-causality-discriminator/README.md)
- [RESULTS.json](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-011-g6-role-causality-discriminator/RESULTS.json)
- [G6-final.md](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/external/codex-cli-cohort-002/G6-final.md)

完整 raw archive 为 `RUN-RAW.json.gz`，解压后约 1.78 MB，由 `RESULTS.json` 的 SHA-256 绑定。

本轮未修改 `NOW.md`、`PROGRAM.md`、Problem、LineContract、MechanismProfile 或正式状态。结果仍是本地有限 synthetic discriminator，不是 X2、现实 Effect、真人 Acceptance、生产恢复或跨域一般性证据。