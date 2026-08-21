G1 第三轮修复已完成，且没有覆盖 same-user hostile OS 红灯。

关键结果：

- A/B/C 已真实独立建立；C 未读 B 的测试、说明或 final。
- owner/worker PID 强制绑定 controller 观察到的实际 `Popen.pid`。
- owner source/state/process 与 worker process instance 绑定 controller assignment。
- 四类来源错配均在转发或评价前 fail closed，包括伪报 `424242`。
- C 发现的 `authority_id → g1_claim_root_id` 语义伪装已删除。
- 原五类语义注入名称不再进入 worker。
- G1 composition envelope 不含合同成功及后线语义；E3 episode ID 改用可复算 hash reference。
- owner 明确标为 `CONTROLLER_HOSTED_SYNTHETIC_OWNER_FIXTURE`。
- `RED_NOT_ISOLATED`、真实 owner/discovery/完整 CE-001 的 `NOT_ESTABLISHED` 均保留。

验证结果：

```text
tests                         35/35 PASS（原 30 + 新 5）
40 consecutive episodes      40/40
identity injections          4/4 FAIL_CLOSED
semantic injections          5/5 INVALID
exact raw relay              96/96
private canary absent        16/16
L_benchmark                  6/9
D_actual                     6/6
manifest                     valid / mismatches=[]
```

最终报告：[G1-fix2-final.md](</Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/external/codex-cli-cohort-003/G1-fix2-final.md>)

冻结输出：[frozen-output.json](</Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-012-ce001-power-restoration/g1-provenance/frozen-output.json>)

```text
bytes           = 1,449,446
sha256          = a3f908e7199d0475d09bd00268bd6074a0cdc31d994eb2c7772cfee17aa8081f
manifest_sha256 = 0a6282a0b679d7d58fc9cc256b6b4370110e466ef6350f763a34e8a557de83c0
```

未修改 contract、NOW、PROGRAM、机制状态、其他六线或现有无关工作区改动。