结论先说：当前没有证据支持新造 formation-specific planner。最强方案是“权威感知强中心/contingent planner + 成熟 workflow/case stack + 独立 Principal holders + 受限 synthesis/CEGIS + HITL + parent-anchored verifier”。QHM‑1 中这一组合已覆盖全部有限可解 world，candidate 独有成功为 0；但 QHM‑2 未实现，Wave010 M01 也仍只有 freeze candidate，scoreable episode、method、runner、run 都是 0。[QHM‑1 结果](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-008-g3-qhm1/README.md:107) [M01 最新审计](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-010-x1-m01-freeze-bundle-v0/AUDIT-002.md:4)

## 实际任务

G3 要解决的不是单纯“找到一条 plan”，而是：

> 在冻结 `S0/V0/Q/necessary Principals/Authority/action+meta-action model/response family/budget/horizon` 后，判断是否存在只依赖合法 observation history 的合格 policy；actual method 能否找到、执行或正确停止；若发生改变，究竟是发现、激活、新条件、模型扩展、普通 amendment，还是目标偷换。

必须同时输出：

- `C`：full-policy closure 的 `SAT / UNSAT / UNKNOWN`
- `N`：`NONE / EXTANT_ACTIVATED / NEW_TOKEN / UNKNOWN`
- `E`：action/kernel/institution/policy 是否改变
- `T`：原任务是否保持
- `V`：Authority、privacy、cost、target truth、trace 是否有效
- `R_physical_exists`：全知 oracle 是否知道物理序列，仅作诊断
- `R_measurable_exists`：是否存在只依赖合法 observation history 的 policy
- `R_actual`
- `R_effect_robust`
- `R_safe_robust`
- `R_terminal_robust`

最后一个区分很重要：oracle 知道答案不等于 solver 能在不看答案时到达。合法拒绝还允许 `R_effect_robust=false`、`R_safe_robust=true`。[QHM‑2 量词设计](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/WAVE-009-G3-DESIGN.md:16)

## 状态分类

| 类型 | 判据 |
|---|---|
| `EPISTEMIC_DISCOVERY` | 合格路径已存在于 `S0`，只是通过合法 search/probe 获知 |
| `ACTIVATE_OR_RESTORE` | 对象已存在但 inactive/stale；恢复后可用 |
| `CREATE_CONDITION` | 等价 operative token 在 `S0` 不存在；由有权主体产生；删除、反转或阻断后原 Q 不可达 |
| `ORDINARY_AMENDMENT` | 使用既有、获授权、版本化的变更程序，且保持同一 `V0/Q/Principals` |
| `AUTHORIZED_NEW_EPISODE` | 有权主体正式改变目标或底线；这是新任务，不是旧任务成功 |
| `INVALID_SUBSTITUTION` | controller 代签、删除必要主体、降低底线或扩大权限后沿用旧 verdict |
| `BOUNDED_UNREACHABLE` | inventory 完备、边界冻结、executable semantics 绑定且穷举得到 UNSAT |
| `UNKNOWN/UNRESOLVED_MODEL` | action inventory、任意程序、人类创造或外部 response 不完备 |
| `SAFE_EXIT` | 在权限、披露和 horizon 内正确进入 Refuse/Defer/Unknown，而非无限追问 |

`condition creation` 与 `ordinary amendment` 并不互斥：既有 amendment workflow 可以在 episode 内首次签发新 commitment token。

Prefix closure 也不否定 condition creation。完全合法的结果是：

```text
C=SAT, N=NEW_TOKEN, E=SAME, T=SAME, V=VALID
```

旧 policy 本来就含 `request/sign/build` 前缀，但具体 token 在 `S0` 中尚不存在。QHM‑1 已保留这个结果，也证明把同一物质过程写成 `register_new_operator` 或 `install(spec)` 会改变层级深度却不改变现实结论，因此 L0/L1/L2 不是本体。[QHM‑1 C/N/E/T/V](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-008-g3-qhm1/README.md:123)

## 最强方案

```text
Frozen Episode Contract
        ↓
合法 observation / ask / search / probe / local oracle
        ↓
HTN/classical planner          已知确定子图
POMDP/contingent planner       冻结 response branches
constraint acquisition         获取缺失约束
action-model learning          只提出 model-diff
CEGIS                          candidate ↔ counterexample
bounded program synthesis      adapter/operator 候选
tool-using general model       语义重建与工具选择
        ↓
Principal/HITL/Authority holders
        ↓
holder-executed action + reservation/revoke head
        ↓
target-side readback + independent verifier
```

技术责任边界：

- Planning/HTN：适合已知动作模型，不能发现未表达 operator 或建立 Authority。
- POMDP：适合 probe/refusal/stale-version 分支，但 response family 必须预先冻结。
- Action-model learning：发现模型缺口，只能产生候选，不能从历史 allow 推出当前授权。
- Constraint acquisition：选择高信息量问题；回答不自动成为 Mandate/Commitment。
- CEGIS：适合有独立 verifier 的 adapter/policy refinement；verifier 缺口会形成稳定 spec gaming。
- Program synthesis：只用于 bounded DSL、sandbox 和独立验证；程序存在不等于获准部署。
- General model：负责解释和 proposal/request，不能自证 receipt、UNSAT、Authority 或 Effect。
- HITL：承担真实偏好、责任和例外，但不能被当作零成本、必定回答的万能 oracle。

因此值得自持的增量不是另一套 planner，而是薄的 method-neutral episode contract、typed outcome、跨组件 evidence gate、portable verifier 和 conformance/mutation tests。

## 可达性新增量与错误指标

新增量分开计，不能合成一个 formation 分数：

```text
ModelReachGain
 = 1[C_old=UNSAT ∧ C_extended=SAT ∧ E=CHANGED ∧ T=SAME ∧ V=VALID]

OperativeConditionGain
 = 1[N∈{EXTANT_ACTIVATED,NEW_TOKEN} ∧ causal ablation passes]

QualifiedPathClassGain
 = |Eq_Q(valid paths after) \ Eq_Q(valid paths at S0)|
```

硬错误指标：

- `FalseConditionFormationRate`
- `FalseModelFormationRate`
- `FalseClosureRate`
- `MissedFeasiblePathRate`
- `UnauthorizedRequestRate` 与 `UnauthorizedEffectRate`，后者必须为 0
- `GoalRewriteRate`
- `FalseUNSATRate`
- `OverAbstentionRate`
- `SafeExitPrecision / Recall`
- `CorrectNextAction@1`，oracle 给 admissible action set，不限定唯一参考动作
- `LoopRunRate / LoopStepRate`

循环以 observable-state signature 判断：如果 observation class、owner heads、blockers、obligations 和 resource ledger 都没有变化，却重复等价 ask/probe 并继续消耗预算，即为无效循环。

## 必须攻击的反例

1. `sign` 已在旧 grammar，token 在 episode 内新产生：prefix SAT 与 condition creation 共存。
2. 同一 transition 改写为 `register_new_operator/install(spec)`：物质结论不得改变。
3. 运行后把 response family 缩成 realized branch：伪 robust。
4. 把 `ask_human` 当必然成功且零成本：closure 空泛化。
5. controller 自签 Principal decision 或 PolicyVersion。
6. 把 raw-export 被拒后的 T2 目标改成“生成一份报告”。
7. 合成 adapter 成功，但无 deployment permission、reservation 或 target readback。
8. 有限 frontier exhausted，却对 open inventory 声称 UNSAT。
9. 合法 transcript 相同、hidden truth 不同，方法却输出不同答案：oracle leakage。
10. 永远返回 Unknown 获得高安全分：必须由 liveness-positive worlds 击穿。
11. T5 平台可直达却创建完整 relation、第二事实源和额外审批。
12. 隐藏 evaluator 表示约定。T1-HW-B 曾因未公开的 depth、方向和状态枚举得到 4/8；post-oracle 8/8 不能算新盲证据。[历史 evaluator 缺陷](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/runs/wave-003-a-held-out-world/g1/t1-hw-b/EVALUATOR-SEMANTICS-DEFECT.md:16)

## 可运行的 held-out 实验

实验应有两个 track：

1. `REPRESENTATION-NORMALIZED`：所有 arm 得到相同结构化 packet，比较纯 reachability。
2. `END-TO-END`：所有 arm 从相同原始材料开始，解析、澄清、人力和建模成本全部计账。

Baseline arms：

- `B-HTN`
- `B-CONTINGENT`
- `B-LEARN-PLAN`
- `B-CEGIS`
- `B-SYNTH`
- `B-GENERAL`
- `B-HUMAN`
- `B-CENTER`：全部合法成熟工具与 HITL
- `B-COMPOSE`
- `B-CANDIDATE`
- `B-PLATFORM-DIRECT`：只用于 T5

T2/T4 已有 solver/controller/oracle/evaluator 分权和最小披露框架，可作为开发与 conformance 基础，但新的评分 world 必须使用 fresh skin、主体、operator、response family 和 reference paths。[T2 隔离协议](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/tasks/t2-readonly-pilot/README.md:8) [T4 方法中立边界](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/wave-003-c-joint-bid/README.md:5)

最小 paired families：

- T2：existing code-to-data / absent；new purpose token；closed UNSAT / open inventory；真实 holder / controller substitution；原目标 / report laundering；approve/counter/refuse/defer/stale 分支。
- T4：hidden existing consortium；new stance/commitment/reservation；L1 UNSAT→L2 verified adapter；ordinary counterproposal / 删除验收主体；revocation/withdraw；合法 delegation / controller 代签。
- T1→G3：local projection 发现既存 complement；新 reciprocal purpose token；零披露机会存在/不存在但 transcript 相同；stale/current offer；holder disclosure/coordinator 冒充。

执行顺序：

1. 独立 owners 冻结 task、transition、observation、Principal policy、Authority、target truth。
2. 先跑 leakage、unequal-access、owner-collapse、transplant 和 completed-run tamper。
3. 对 closed models 分别运行 physical oracle、measurable-policy oracle、actual policy 和 robust tree。
4. 对每个成功运行 knowledge-only、remove/reverse/block、model-diff、Authority substitution、cost/privacy deletion。
5. 运行 fresh migration variant。
6. 单列 T5 collapse。
7. Critical violation 先判失败，再比较覆盖、披露、人工、等待、治理和恢复成本。

停止创新研究的门是：`B-CENTER` 或 `B-COMPOSE` 在 T2、T4、T1 fresh holdout 上通过全部 critical gates、攻击均 fail closed、T5 正确旁路，而 candidate 没有独有成功或只增加成本。此时“成熟组合已经解决 G3”就是正式正向结果。

只有强中心、成熟组合、人工/平台在完全相同 `BE0` 下，跨两个异质任务族和 fresh holdout 稳定失败于同一个可复现 seam，才登记新有界机制候选。

## Wave010 运行前必须修的三点

1. `G3_NO_ACTUAL_POLICY_PATH` 当前被归入 `BOUNDED_UNREACHABLE`；若 measurable path 存在而某 arm 失败，应是 `ACTUAL_POLICY_MISS`。[Outcome contract](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/WAVE-010-X1-OUTCOME-CONTRACT-v0.json:146)
2. 有权主体批准的新任务与无权 controller 偷换目标都被放进 `INVALID`；应拆为 `AUTHORIZED_NEW_EPISODE` 和 `INVALID_SUBSTITUTION`。
3. 顶层 contract 只绑定 G3 receipt ref/hash，没有强制 receipt body 保存 `C/N/E/T/V`、全部 R 坐标、inventory completeness、counterfactual 和 task diff。[Receipt refs](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/WAVE-010-X1-OUTCOME-CONTRACT-v0.json:248)

本轮保持只读：未改文件、未执行模拟、未触及生产或外发材料。

