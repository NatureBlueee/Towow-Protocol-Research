第二次根红灯修复已完成，修改严格限制在 `g4-reliance/` 和 `G4-fix2-final.md`。

关键结果：

- O_E/O_Q/O_V 改为三个实际 child process，绑定真实 PID、process instance、service/state/act source 和进程内 Ed25519 key。
- 公开 SHA 重算、未调用 owner child、重复 service/source、signature replay 均不能闭合。
- PENDING、0kW、C8、其他线路、短时长、deadline、错误 O_E provenance、未 exact reconciliation 均在 owner request 前拒绝。
- 显式 adapter 将 `Venue-V/Circuit-C7` 对齐 `VenueV:CircuitC7`，无静默字符串替换。
- G4 输出已移除全部 `Y_*`、`ExactTaskSuccess` 和合同级字段。
- 原 19 项覆盖保留，扩展为 B `35/35 PASS`。
- C 独立最小复核 `8/8 PASS`。
- integration preflight `14/14 PASS`。
- `runner.py --self-test`、`py_compile` 和 JSON 校验通过。

完整证据、失败历史和边界见 [G4-fix2-final.md](</Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/external/codex-cli-cohort-003/G4-fix2-final.md>)；实现说明见 [README.md](</Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-012-ce001-power-restoration/g4-reliance/README.md>)。

真实 owner act、现实 Effect/Acceptance、一般 calibration 和完整 CE-001 仍为 `NOT_RUN/NOT_ESTABLISHED`；本轮没有提交或正式状态晋升。