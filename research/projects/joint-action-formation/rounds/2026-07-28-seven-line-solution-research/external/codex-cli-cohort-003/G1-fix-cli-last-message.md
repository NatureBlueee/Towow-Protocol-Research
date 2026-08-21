根红灯已修复，但结论严格限定在 cooperative process/API 边界。

- method worker、owner service、controller 为三个独立 PID。
- 16 次冻结运行记录了 64 个 worker 入站 frame、52,176 bytes、96/96 exact-byte relay。
- 私有 `expected/L/D/oracle/canary` 确实存在于 controller/evaluator 输入，未进入 worker；反射、closure、frame、GC、import、env、argv、临时 cwd 扫描均未命中。
- `D_actual=6/6`，`L_benchmark=6/9`；E2 为 `QUALIFIED / UNKNOWN / INVALID`；5/5 failure injection 均为 `INVALID`。
- 最终测试 `30/30 OK`；另连续运行 40 个 process episode，无超时。
- same-user absolute-path probe 仍为 `RED_NOT_ISOLATED`，不声称 hostile OS isolation、独立 evaluator PID 或真实 O_R/O_V 权限域。

完整结论与红灯历史见 [G1-fix-final.md](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/external/codex-cli-cohort-003/G1-fix-final.md:7)。

冻结输出见 [frozen-output.json](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-012-ce001-power-restoration/g1-provenance/frozen-output.json)，SHA-256：

`e333359dedbfc538558b6839d040f58ca928007559e60869fb438674567aadec`

本轮只修改了获准的 `g1-provenance/` 和 `G1-fix-final.md`。