G5 CE-001 根红灯已修复，且只修改了 `g5-authority/` 与 `G5-fix-final.md`。

关键结果：

- target 直接验证 signed owner receipts、canonical U/D/P topology、exact Q/object/revision/scope/expiry、Standing、current owner heads 与 resource fence。
- 14/14 target-native 攻击拒绝，全部 0 transition。
- 12/12 race cells 正确闭合。
- 3/3 Saga 实际执行 `ENERGIZE → DEENERGIZE → readback OFF`。
- C 发现并击穿了第一版 migration epoch；现已改为 authority-channel 签发单调 takeover lease，并由真实 old-source-restarted 第三 PID 完成 stale replay。
- migration 最终仅 1 次 Effect，`duplicate_effect=false`。
- root：`13/13 PASS`，runner `COMPLETE_LOCAL_COMPONENT_MODEL`。
- 独立 C：`13/13 PASS`，migration 定向攻击全部通过。
- manifest 的 5/5 artifacts、12/12 source hashes 匹配；未发现 private key material。
- `OPA/Cedar/OpenFGA/XACML/CROSS_FAILURE_DOMAIN_MIGRATION` 均保持 `NOT_RUN`。

交付文件：

- [G5-fix-final.md](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/external/codex-cli-cohort-003/G5-fix-final.md)
- [g5-authority README](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-012-ce001-power-restoration/g5-authority/README.md)
- [results.json](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-012-ce001-power-restoration/g5-authority/artifacts/results.json)
- [manifest.json](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-012-ce001-power-restoration/g5-authority/artifacts/manifest.json)

剩余边界已明确保留：trusted bootstrap、可靠 owner-event ingest 和 shared durable store 仍是假设；恶意 revoke withholding、现实 lawful Authority 与跨故障域迁移尚未证明。