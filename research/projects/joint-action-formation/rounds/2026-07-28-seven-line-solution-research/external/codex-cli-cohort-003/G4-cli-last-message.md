G4 reliance/outcome module 已完成，且仅写入指定目录及 `G4-final.md`。

关键结果：

- 强制 `P0 → interaction → P1 → reservation → commit evidence → attempt → 四 outcome`。
- E3A/E3B 判定为 `ACTIVE` pair；正确处理 ACK-loss、wrong-object readback 和安全重试。
- 并发重复投递：2 deliveries、1 Effect、0 duplicate。
- 撤销压力：0 attempt、0 unsafe Effect。
- 预测校准与本地 world-change delta 分开评分。
- 修复了 evaluator 依赖 worker 自报 wrong-object 判断的问题。
- 最终验证：`11/11 PASS`、`SELF_TEST_PASS`、`py_compile PASS`。

交付：

- [G4-final.md](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/external/codex-cli-cohort-003/G4-final.md)
- [模块 README](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-012-ce001-power-restoration/g4-reliance/README.md)
- [失败历史](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-012-ce001-power-restoration/g4-reliance/FAILURE_HISTORY.md)

证据边界保持为本地 component model；独立 truth-author blind holdout、真实产品和现实供电均为 `NOT_RUN`。