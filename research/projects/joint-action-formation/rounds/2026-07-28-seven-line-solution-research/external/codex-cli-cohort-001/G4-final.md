## 总判断

Wave010 的 12-world 数字必须正式降级为：

`DEVELOPER_AUTHORED_CONFORMANCE_FIXTURE / ALIAS_BY_CONSTRUCTION / NOT_HELD_OUT / NOT_INDEPENDENT / NO_COVERAGE_CLAIM`

它只保留两项价值：

- 把 capability、permission、reservation、attestation、recovery、Authority 与 reliance 的非蕴含关系做成 decision table；
- 给出一个条件成立的不可观察性反例。

它不证明成熟组合覆盖 T2/T4/T6，不证明行业方案已闭合，也不证明 strong center 与成熟组合经过公平比较后等价。

### exact-operation reliance

正式对象应冻结为：

\[
x_t=(operation, executor, environment, artifact/version, distribution,
permission, resource, recovery, horizon)
\]

\[
\hat y_t=\pi(O_t(x_t))\in\{RELY,BLOCK,ABSTAIN\}
\]

`RELY` 只表示：当前 lawful observations 足以把这个 exact operation 交给随后的 execution-time Authority gate。它不创建 Mandate、Commitment、Execution、Effect、Adoption、Acceptance 或 G7 affected closure。这符合 V1/V2 的非蕴含边界，以及 G4 LineContract 的 attempt-before-prediction 要求。[Problem V2](/Users/nature/通爻协议研究/research/projects/joint-action-formation/problem/v2.md:123) [G4 LineContract](/Users/nature/通爻协议研究/research/projects/joint-action-formation/lines/04-capability-realization-v2.md:9)

- T2：绑定只读 aggregation operation、容器 digest、buyer sandbox、query set、当前数据权限、compute/audit reservation、recovery operation 与 horizon；买方目标域 readback 仍属于独立后续事实。[PROGRAM](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/PROGRAM.md:78)
- T4：绑定三方 exact interop chain、tender addendum、三项原子 reservation、各自商业/技术 Authority stance；技术 capability 不能推出容量、价格或签署。
- T6：此前成功只能是 prior。任何 model、container、environment、permission、dependency 或 recovery coordinate 改变，都形成新的 tuple；恢复本身也是需要重新资格化的 exact operation。[PROGRAM](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/PROGRAM.md:150)

若两个 world 满足 \(O_t(w_a)=O_t(w_b)\)，但 safe truth 相反，则任何 packet-only 确定性策略只能输出同一动作：`RELY` 会在 unsafe world 误承诺，`BLOCK/ABSTAIN` 会漏掉 safe world。强中心或通用模型在相同 observation/action budget 下不能突破；只能创建新 observation、请求 owner disclosure，或保留 Unknown。[Wave009 G4 设计](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/WAVE-009-G4-G6-G7-DESIGN.md:138)

## 12-world 为什么是构造配合

最直接的 alias-by-construction 是：

- `strong_center()` 直接调用 `mature_composition()`，不是独立实现。[Simulator](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/WAVE-010-G4-RELIANCE-SIMULATOR.py:96)
- self-test 再硬断言两臂完全相同及目标指标。因此“两者 precision 1.0、recall 0.75”是代码恒等式，不是比较结果。[Simulator](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/WAVE-010-G4-RELIANCE-SIMULATOR.py:271)
- `mature_composition` 直接读取已经预消化的 `FAIL/REVOKED/CONFLICT/MISSING/SHIFTED/UNKNOWN/HIDDEN` 字段；策略分支与手写 oracle 原因逐项同构。
- “recovery accuracy”只比较返回字符串与 `required_recovery_action`，没有执行 recovery，也没有 target-owner readback。[Simulator](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/WAVE-010-G4-RELIANCE-SIMULATOR.py:191)
- `head_current` 是 fixture 直接给出的布尔答案，没有从 Authority head/epoch 计算；因此没有重测 Wave007 曾暴露的合法旧 `ACTIVE` receipt 覆盖 current `REVOKED`。
- hidden pair 实际向候选暴露了 `kind="HIDDEN"`。真正 undeclared dependency，以及 `DECLARED + query_supported=false` 都没覆盖；后者在当前代码中会直接落到 `RELY`。
- 12 worlds 没有有效的 multi-fault、reservation expiry、query timeout、owner latency/refusal、TOCTOU、correlated evidence 或实际成本日志；所有 `recovery_evidence` 都是 `PASS`。

fixture 自己也明确排除了现实 capability、production reliability、真人 Authority/Acceptance、现实频率和新机制必要性。[Fixture](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/WAVE-010-G4-RELIANCE-FIXTURE.json:4)

### 真实覆盖

当前不能报告现实覆盖百分比，因为没有合格现实分母。可核实状态是：

- Wave010：12 条 developer decision-table rows；
- Wave007 C2：15 个本地合成 worlds，修复了三个已知攻击，但仍是同研究者 repair regression，不是 blind holdout、独立实现或现实 Authority 验证。[C2 README](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-007-c2-access-metered-reliance/README.md:123)
- Wave009：G4 仍为 `evaluator/spec only`，没有前瞻覆盖率；T6 没有合格 base trace 或 oracle dependency graph。[Wave009 第二返回](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/WAVE-009-SECOND-RETURN.md:223)

所以现实企业/生产、独立 held-out、真实 recovery readback 和完整 G4→G5→G6→G7 闭环均为 `NOT MEASURED / NOT RUN`，不是 12-world 的 1.0。

## 行业技术的公平结论

| 方法 | 可闭合切片 | 不自动蕴含 |
|---|---|---|
| CI/eval、exact probe | exact technical operation | permission、capacity、recovery、未来 head |
| readiness、telemetry | health、shift signal | exact success、授权、责任变化 |
| IAM、reservation | current permission；ledger 域内 exclusivity | capability、签署、Effect |
| workflow、attestation | durable execution；provenance/substitution | target truth、liveness、current regime |
| owner HITL | 风险、责任、授权和 material change | machine head、probe、原子容量 |
| 通用模型、强中心 | query/probe/HITL 选择与组合编排 | hidden fact、owner 权威、目标域事实 |

成熟组合在“依赖已表达、heads 可查、probe 有覆盖、reservation 原子、recovery 有独立 readback、owner 可响应”时仍是当前首选方案。行业技术尚未在本地证据中闭合，是因为这些组件尚未被独立集成为 truth-preserving chain，也未在相同 lawful API、预算、时延和迁移条件下运行；不是因为已证明行业没有解。[Wave010 方法矩阵](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/WAVE-010-G4-RELIANCE-FRONTIER.md:49)

## 下一项唯一独立实验

建议冻结：

`G4-HO-001 / FINALIZED-X1-OUTPUT-PROSPECTIVE-RELIANCE`

前置门是实际 finalized、execution-eligible 的 X1 T2/T4 output；此前继续手写“成功 X1”只会再造 fixture。Wave010 正典也要求 X2 机械接收实际 X1 outputs，目前尚未运行。[Wave010 Start](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/WAVE-010-START.md:45)

实验要求：

1. truth owner、packet compiler、候选实现和 evaluator 四方分离。
2. packet 只含 opaque、owner-signed raw receipts、heads、leases 和 probe records；禁止发送 `head_current=true`、motif、A/B、expected outcome 等答案型字段。
3. 比较成熟组合、独立 strong center、general-model controller、owner-HITL；禁止共享决策函数。
4. 所有 arms 使用同一 observation/action API、Authority、预算、timeout 与 horizon；parent broker 独立记录 bytes、latency、query、probe、HITL、拒绝和重试。
5. 必须包含：
   - declared-but-unqueryable 与真正 undeclared dependency；
   - validly signed stale `ACTIVE` head；
   - permission + reservation + version 等 multi-fault；
   - workflow self-report recovered、但 target-owner readback 缺失或版本不符；
   - observation 成本低但超时，以及昂贵 observation 能消除 Unknown 的对照。
6. prediction 必须先冻结，再揭示 drift 与实验内权威 recovery readback；事后修复不能回填预测。
7. 先通过 rename、world-name routing、stale replay、identity spoof、log clear、all-abstain、post-hoc prediction 和 same-transcript leakage gates，再启用评分。
8. 分项报告 false reliance、missed viable、abstention/selective coverage、evidence correlation、首次成功、恢复时延以及 observation/HITL/资源占用的全成本；不预定任意 world 总数。

只有在两个异质任务族和独立 held-out 中，成熟组合、强中心和通用模型在完全相同条件下仍留下同一个稳定 residual，并排除了缺 observation、owner 不响应、预算不足和 adapter 未实现，才有资格提出新机制。目前最可能需要的只是一个不制造第二事实源的跨来源资格化/conformance gate，尚不是已证明的新协议缺口。

本轮未联网、未修改文件、未运行生产。