# 研究契约

这里的 Schema 只保护会影响判断的边界，不规定研究结论或统一理论。

- `ProblemContract` 决定正在研究什么，以及什么会推翻或重开它。
- `ScenarioContract` 把抽象问题绑定到可判别的具体世界、权威和结果。
- `LineContract` 允许异构研究线保持自己的问题与失败机制。
- `RunManifest` 固定一次运行实际看见的输入、工具和成本。
- `ResearchResult` 强制区分观察、来源、推断、设计建议和负结果。
- `ClaimCandidate` 记录主张的证据边界；自动研究不能把它晋升为 `STABLE`。
- `MechanismProfile` 保存一个有界机制的原始问题、适用前提、逐项 scoped claim、非目标、
  证据状态、开放问题和无损替代条件；`identity_criticality` 与 `portability` 分开，假说 ID、
  来源和运行状态不绑定 NAC 的历史命名；它不是新的运行时本体。
- `HistoricalInheritanceAudit` 不要求旧术语继续成为正式对象，但要求每个历史设计能力都有
  明确的保留、降级、缺口或有证据拒绝去向。默认项目中的候选与激活问题不得省略它；
  `ACTIVE` 问题还必须绑定与当前问题同版本、状态为 `REVIEWED` 且建议为 `READY` 的审计。
- `ProblemActivationBundle` 冻结一次问题激活所依据的五份材料：候选机器契约、候选人类说明、
  当前版本继承审计、审计说明与正典能力矩阵。它本身不授予激活权；用户决定还必须绑定
  bundle 的路径与 SHA-256。

`ProblemContract 2.0` 必须提供带 SHA-256 的前序快照和结构化 `shared_basis`；
`LineContract 2.0` 必须绑定有界研究目标、已有方案检查和只影响 scoped claim 的结果策略。
每次 Run 还会冻结实际 `hypothesis_ids` 与 `tested_claim_ids`。对应的 `ResearchResult 2.0`
必须逐项返回这些 scoped claim 的候选变化和未受影响主张；运行器拒绝一条线修改本次运行
焦点之外的机制主张。完整 RunInput 既有排除运行 ID 的语义哈希，也有实际 `input.json`
字节哈希；Plan 2.0 还会重新计算不可变规划字段的指纹，并把内嵌的问题、场景、研究线、机制
与来源逐项对回正典内容。运行、恢复、盲审和 finalize 都重验同一输入。机制盲审按
`anonymous_return_id + hypothesis_id + claim_id` 的冻结单元逐项覆盖，允许不同单元对同一
主张保留冲突，不再按 claim 全局合并，也不把机制批次退化成 V1 问题激活建议。
`GAP_CONFIRMED` 必须引用真实存在且已进入 allowlist 的历史与现成方案材料，并逐项说明缺口。
正式机制状态、Problem 激活和稳定主张必须绑定用户决定中的精确 source/content hash；
`ProblemContract 2.0` 的激活还必须绑定可重新验证的 activation bundle hash。
MechanismProfile 中已支持、反驳或已执行的状态还必须引用 finalize packet 内的结果、证据
receipt、Plan snapshot 与完成态 RunManifest snapshot，并同时绑定输入、受检验 scope 和
当时的主张/假说定义哈希；`FAILED`、`REFUSED` 和 `NOT_RUN` 不能转为机制证据。每个正式
profile 本身也必须由用户决定登记精确内容和状态快照；`VALIDATED_SCOPED` 只能列明有证据
闭包覆盖的 claim、hypothesis 与 capability。Claude 评审只有在 payload、disclosure、
原始返回、结构化结果、模型和批准决定都由 execution receipt 绑定后才能附入候选包。
Scenario 晋升保留候选原像和独立 ACTIVE 快照，运行前持续验证 source/target 双哈希 receipt。
Problem 晋升还把 ACTIVE 人类说明作为候选说明的确定性投影写入 receipt；ACTIVE 契约、说明
与 receipt 已闭合后才更新 `NOW.md`，中断重跑只续写完全相同的投影，不覆盖冲突文件。
1.0 合同继续作为历史快照保留，不被追溯改写。

运行器还为 Plan、完成结果和盲审建立只写一次的本地 controller seal，并在 review、
finalize 和候选包重读时重新校验原始输出、事件流、结构化结果与冻结输入。这些 seal 的明确
威胁模型是“受信任 controller + 只读 worker”：它们阻止正常流水线和普通漂移静默替换结果，
但 `0444` 不是抵抗拥有同一目录写权限之恶意本机进程的密码学不可篡改证明。若研究结论需要
覆盖该威胁，必须另用 controller-only 权限域、append-only 外部锚、Git object 或签名。
可变 controller JSON 通过同目录临时文件原子发布，避免中断留下半个状态文件；候选包则先
在 staging 完整构造并深验，再一次性发布。已经带 finalization manifest 的候选包不再原地
补挂盲审或其他证据；迟到材料必须进入新的批次或 append-only revision，保留原包字节不变。

Schema 通过 `python3 tools/researchctl.py validate` 校验。完整状态转换和人工门禁由
`researchctl` 的语义检查负责，不能只依赖 JSON 字段合法。
