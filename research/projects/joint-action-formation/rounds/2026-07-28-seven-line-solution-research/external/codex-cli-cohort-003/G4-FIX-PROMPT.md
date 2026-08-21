# G4 CE-001 根红灯修复任务

你是 G4 独立 Codex CLI 主会话的第二轮。先完整读取：

- `COMMON.md`
- `G4-PROMPT.md`
- `ROOT-LIVE-AUDIT.md`
- `../../experiments/wave-012-ce001-power-restoration/g4-reliance/`

必须实际建立 A/B/C 三个内部 Agent：A 独立重建 Acceptance/Resolution 真值边界，B 实现，
C 在不知道期待结果的情况下复核重复 owner、wrong episode/Q/effect、stale act、拒绝和
one-class calibration。主会话负责整合和最终解释。

只可修改：

- `../../experiments/wave-012-ce001-power-restoration/g4-reliance/`
- 本目录 `G4-fix-final.md`

不得修改 NOW、PROGRAM、Problem、LineContract、Mechanism、Scenario、其他主线目录或
`ROOT-LIVE-AUDIT.md`。

必须关闭以下实际红灯，而不是只改文字：

1. 同一 service 不得在 Effect 时自动替 O_Q/O_V 生成 Acceptance；
2. O_Q/O_V 必须由独立 owner state/service 分别产生 act；
3. Acceptance closure 必须恰好覆盖 required owner set，验证唯一 issuer、
   `episode_id/Q_version/object_id/operation_id/effect occurrence`、current revision 与
   provenance；重复同一 owner 不能增加闭包；
4. 加入 Effect 已发生但一个 owner 拒绝、wrong episode、wrong Q、wrong effect、
   stale acceptance 和 duplicated owner mutation；
5. 加入至少一个真正 `Y_resolution=false` 的 case，使 P1 resolution 不再是 one-class；
6. matched no-interaction twin 只保留为当前状态机内必要条件，不得写成方法优势；
7. 保留现有 E3A/E3B、wrong-object、double-submit、revoke 回归。

最终返回真实测试分母、失败历史、当前能支持和不能支持的最窄结论。真实产品、真实供电、
真人 Authority/Acceptance 仍然是 `NOT_RUN`。
