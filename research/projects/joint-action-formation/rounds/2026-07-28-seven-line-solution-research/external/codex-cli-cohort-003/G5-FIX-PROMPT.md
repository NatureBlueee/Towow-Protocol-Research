# G5 CE-001 根红灯修复任务

你是 G5 独立 Codex CLI 主会话的第二轮。完整读取 `COMMON.md`、`G5-PROMPT.md`、
`ROOT-LIVE-AUDIT.md`、`G5-final.md`、现有 `g5-authority/README.md` 和
`FAILURE_HISTORY.md`。

实际建立 A/B/C：A 重建 target enforcement 与 Authority truth 边界，B 实现，C 独立尝试
绕过 owner receipt、注入 controller fence、配置 owner truth、复用旧 migration state 和
把 Saga action 当作恢复结果。

只可修改 `g5-authority/` 和本目录 `G5-fix-final.md`；不得修改其他路径。

必须：

- target execute 必须实际消费并验证 current signed owner receipts、exact operation、
  Q/object/scope/revision/expiry、standing 与 fence；不能只信 controller 的
  `authority_allowed` 或顺序；
- fence/current head 必须从 owner/authority channel 到 target，controller 不能裸注入结论；
- U/D/P 明确各自 Authority topology；相同代码可以复用，但不能用配置标签自证合法性；
- post-check revoke、wrong owner、stale head、changed Q/object 和 forged receipt 必须在
  target-native gate 被拒绝；
- Saga 必须以 target-native `ENERGIZE → DEENERGIZE → readback OFF` 证明补偿，不以动作记录
  自证；
- migration 至少拆分 source/target runtime process，并说明共享 durable store 只证明何种
  restart；若不能跨故障域，保持 `NOT_RUN`；
- 保存 PID/key/source/input/raw/result/manifest，并复跑全部现有 race/validation。

OPA/Cedar/OpenFGA/XACML 未实际安装运行时继续写 `NOT_RUN`；本地 reference engine 不冒充
产品。
