已完成并仅写入指定 `wave-011-g5-authority-conformance/` 目录。

核心结论：MCB-G5-v2 discriminator 已完成，但当前证据仍不支持 canonical IR 或新 Authority 协议。强中心、成熟组合、CLM/HITL、人类规则均保留完整胜出路径。

关键结果：

- A/B/C 三名内部研究者已真实并行运行并交付。
- 四个 owner 使用独立 PID、store、Ed25519 key，可分别 reject/revoke/outage/fork。
- U/P 技术权限完全相同；permission-only center 在外部 non-delegable right 世界产生 false allow。
- 实际运行 50 个 race cells：
  - 无共同事务：4 个 transient stale Effect。
  - bounded confirm：0 个。
  - 2PC-like hold：安全，但 10/10 持锁阻塞。
  - Saga：4 个 Effect 发生后补偿，未冒充原子。
- Target ignore、restart-loss、cross-region reorder 均产生 stale Effect；strict fence 正确拒绝。
- 本地 subprocess policy engine 实际运行 7 cases。
- 13 个 OPA/Cedar/OpenFGA/XACML adapter-shape cases 通过，但四个真实产品均明确 `NOT_RUN`。
- 主实现 `6/6` tests、B 独立实现 `10/10` tests，compileall、JSON 和 runner 校验通过。
- 未修改 NOW、PROGRAM、LineContract 或正式状态。

主要交付：

- [G5-final.md](</Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-011-g5-authority-conformance/G5-final.md>)
- [README.md](</Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-011-g5-authority-conformance/README.md>)
- [results.json](</Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-011-g5-authority-conformance/artifacts/results.json>)
- [manifest.json](</Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-011-g5-authority-conformance/artifacts/manifest.json>)

