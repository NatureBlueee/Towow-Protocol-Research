G3 根红灯已修复；当前结果是“局部 envelope 可进入 integration preflight”，不是 CE-001 合同成功。

关键结果：

- owner、public worker、grader 已形成真实 subprocess 边界。
- owner raw JSONL 经 broker 逐字节原样传给 worker，三方逐行 hash 一致。
- 14 类 identity/state/policy/episode/Q/target/operation/request/proposal/stale/tamper 变体全部 fail closed。
- worker allowlist 阻断 private truth、scorer、runner、tests、outputs 与历史答案回读。
- E2 remove 后 proposal/sign/token/submit/readback 全为 0，无已观察旁路。
- E4 只输出 post-revoke bounded reachability observation，不输出合同 verdict。
- 最终 G3 envelope 无合同字段及同义结论。
- 完整 response tree、真实产品、真人 Principal、法律 Authority、物理 Effect 和 CE-001 合同解仍为 `NOT_RUN / NOT_ESTABLISHED`。

验证结果：

- G3：`26/26 PASS`，ResourceWarning 作为错误处理。
- integration-preflight 当前：`14/14 PASS`。
- 最终 envelope：`QUALIFIED_COMPONENT_OUTPUTS`、`CONTRACT_SCORE_NOT_COMPUTED`、`rejections=[]`。
- 产物：11 个 line receipts、16 个 raw runs。
- report body SHA-256：`445b016aac078be71458b71e6749387697c3203e958433cc7184f925735dfabf`。

主要交付：

- [G3-fix-final.md](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/external/codex-cli-cohort-003/G3-fix-final.md)
- [README.md](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-012-ce001-power-restoration/g3-formation/README.md)
- [C2-adversarial-audit.md](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-012-ce001-power-restoration/g3-formation/internal/C2-adversarial-audit.md)
- [report.json](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-012-ce001-power-restoration/g3-formation/outputs/report.json)

未修改 `NOW.md`、contract、PROGRAM、Problem、LineContract、MechanismProfile 或 integration-preflight。

