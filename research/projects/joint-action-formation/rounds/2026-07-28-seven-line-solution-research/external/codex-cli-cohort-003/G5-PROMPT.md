# G5 任务

按 `COMMON.md` 执行。只写：

`experiments/wave-012-ce001-power-restoration/g5-authority/`

为 CE-001 构建 G5 Authority/race/fence module：

- U/D/P 三个 Authority stratum；
- owner-native outcome、exact object/version/scope/expiry；
- read/sign/reserve/execute 每边界 revoke；
- target 必须实际执行 fence，不能由 controller 填 `CORRECT`；
- Saga 必须实际执行 compensation target transition/readback，不能只记录 intent；
- material operation closure、Standing、migration loss；
- OPA/Cedar/OpenFGA/XACML 未实际运行就保持 `NOT_RUN`。

最终写 `external/codex-cli-cohort-003/G5-final.md`。
