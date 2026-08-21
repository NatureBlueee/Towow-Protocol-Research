# G1 任务

按 `COMMON.md` 执行。只写：

`experiments/wave-012-ce001-power-restoration/g1-provenance/`

为 CE-001 构建 G1 provenance module：

- clarification prelude 与 `IntentAtCoordinationInterface` 明确分界；
- candidate/resource/partner discovery 的合法 evidence path；
- `L_benchmark` 与 `D_actual`；
- invalidity-first gate、事件向量、source/Authority alias；
- t0 replay、operator removal/reversal；
- 不让 method 读取预枚举“正确 path”或 final proposal。

模块输出必须能被后续组合 runner 消费，但不要实现其他六线。
最终写 `external/codex-cli-cohort-003/G1-final.md`。
