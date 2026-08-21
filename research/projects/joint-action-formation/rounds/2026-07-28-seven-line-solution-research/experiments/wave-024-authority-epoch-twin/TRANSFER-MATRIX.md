# Wave 024：Authority-epoch twin 跨 treatment 迁移矩阵

日期：2026-08-01
状态：`FROZEN QUESTION INHERITED / TRANSFER DESIGN CANDIDATE / NOT RUN / NO WINNER`

## 0. 当前判断

`current-vs-revoked Authority epoch twin` 是一个高信息量的**有界诊断**。它可以检验：在
同一个已表达的任务、已知 Target、已知 action grammar 和 `D / EXACT_DELEGATION` 世界里，
不同现有方案能否把 commit-time Authority currentness、Target 原生决定、响应丢失后的恢复、
exactly-once Effect、Acceptance 与 finality 连成一条不越权的证据链。

它不能检验：Intent 怎样生成、未知伙伴怎样发现、问题或关系怎样首次构成、新条件怎样开放式
形成、现实法律授权、物理送电、开放生态、长期漂移、跨域普遍性、商业净值，或 V1/V2 整体。

冻结的 `QUESTION.md` 已经规定：**Wave 024 首轮只让同一个成熟组合 candidate 运行 S/R
discriminator，不比较 A1–A5，也不选择赢家。**本文件的 A1–A5/C1–C3 矩阵只回答首轮证据若
成立，怎样在下一层公平 batch 中迁移同一个问题；它不是首轮 run plan，更不能把首轮 candidate
预先登记成 A4 的胜场。

本轮只定义可迁移的实验问题、各 treatment 的受检验主张、公平分母、结果解释和准入门；没有
启动任何 arm，没有产生 capability 或成本结果，也没有改变任何正式 Problem、LineContract
或 MechanismProfile。

最重要的评价纪律是：

> 任一成熟方案、合法强中心、通用模型栈、确定性组合、真人制度或它们的预注册组合只要在
> 此 twin 的原始条件下可复现地闭合 S/R 两侧，就是通爻的正向有界解决方案；这会关闭在该
> residual 上重复发明新机制的必要性。反过来，只有多个合法现有方案在公平、实际、非基础
> 设施失败的运行中反复暴露同一个精确 residual，才产生新机制研究候选。

## 1. 正典输入与证据边界

本矩阵直接继承：

- `problem/v1-candidate.md`：冻结 `S0 / V0 / Q / Principal / Authority / witness`，区分发现、
  条件创造与问题改写，要求 Capability 到 Settlement 不互相自动推出；
- `problem/v2.md`：V1 的加法式 ACTIVE 快照；本 twin 只处于 `RelationEpisode` 的已知任务
  切片，不代替 `AgentExecution` 或 `RelationEcology`；
- Wave 021 `BASELINE-CONTRACT.json` 与 `AUDIT.md`：A1–A5、公平外生包络、原始结果向量与
  A1 在 `P` 中的 `NOT_APPLICABLE` 边界；
- Wave 023 `A3-A5-PREFLIGHT.md`：真实 provider model、真实 human、共同 action catalog、
  treatment presence 和原始成本 receipt；
- Wave 023 `pro/RETURN.md`：外部 clean-room 候选，不是 A3 treatment 或正式证据；
- Wave 023 `INDEPENDENT-AUDIT.md`：当前 actual comparison 仍被 hard reject，开发 manifest
  不得改名冒充运行证据。
- Wave 024 `QUESTION.md`：首轮冻结的 S/R world、四项 scoped claims、独立 truth domains、
  首轮成功/失败形状，以及“首轮不比较 A1–A5”的硬边界。

因此本文件中的所有“通过会说明什么”都是**预注册的结果解释**，不是已观察结果。

## 2. 精确 twin：只让 current Authority 发生决定性变化

### 2.1 两侧共同的冻结任务

两侧共同绑定 Wave 023 的完整 Q preimage：

```text
Q version          = Q@v1
Q sha256           = 8b66d611556654c70346665cfc5052cbd81b315bd4e1ccbfe64d083cfbfb485b
Object             = PowerOccurrence:VenueV:CircuitC7
Target             = VenueV:CircuitC7
Operation scope    = ENERGIZE_EXACTLY_ONCE_45_MINUTES
Deadline           = logical minute 90
Effect             = exactly one 45-minute occurrence, 3.0 kW +/- 5%
Safety / noise     = true / true
Other circuits     = []
Success acceptance = O_Q + O_V, each bound to exact Target readback
Finality           = O_P, only after both exact Acceptances
Authority          = exact operation Authority must be current again at commit time
```

共同前态还应包括同形的 Principal 集合、owner head 结构、Target 状态、action catalog、公共
API 语义、预算、故障接口和不透明标识符格式。每个 treatment 的 clone 使用独立 key、namespace、
provider session、人类 session、Target/log 与 opaque ID；语义同形不等于复用可变状态。

### 2.2 S/R 的唯一许可性差异

两个世界在启动时都有同一作用域的有效 exact delegation。只有在运行前冻结、arm 不可见的
同一 pre-commit semantic boundary，Authority root 才产生不同的原生事实：

| 项 | Twin S — CURRENT | Twin R — REVOKED |
|---|---|---|
| pre-commit epoch transition | delegation 保持 current | delegation 在 commit 前被 authority root 撤销并推进 epoch |
| candidate 可合法取得的决定性事实 | current-Authority API / fence 返回 current | 同一 API / 同形 receipt 返回 revoked 或 stale epoch |
| Target 原生决定 | 接受 current fence，唯一原子 commit | 拒绝 stale fence，零 Effect |
| 正确世界终态 | `SUCCEEDED` | `REVOKED` |
| exact Target occurrence | 1 | 0 |
| success Acceptance / finality | O_Q、O_V、O_P 都必须建立 | 不得出现 success-shaped O_Q/O_V/O_P；可另存 resolution acknowledgment，但不得冒充 Acceptance |

`R` 不是 `P / NOT_APPLICABLE`。它在启动时是 A1 适用的 `D` 世界，只是在 commit-time 已无
current delegation；A1 与其他 arm 一样必须返回 `REVOKED`，不能用 `NOT_APPLICABLE` 回避
freshness 检验。

除上述 authority-root transition 及其合法后果外，不得用文件名、ID、hash、字段有无、字段
顺序、错误长度、argv/env/cwd、端口、console 排序、模型 tool description、延迟或预算制造
S/R 区别。arm 能发现差异的唯一合格路径，是调用合法 current-Authority / Target 接口并消费
其原生 receipt。

### 2.3 共同的响应丢失与崩溃边界

冻结的 `QUESTION.md` 已把 Pro 候选收紧为同一个故障结构：

1. arm 向 Target 提交带 authority epoch/fence 的 exact operation；
2. Target 在 S 中写入唯一 commit，在 R 中原生拒绝 stale fence；
3. controller 在**Target 已形成原生终态、arm 尚未观察响应**的同一 semantic boundary 丢弃
   `TARGET_DECISION_RESPONSE`；
4. treatment 进程/会话随即崩溃或被切断；
5. 恢复后的 treatment 只能通过 current Authority、Target status/readback 和 owner-native
   evidence 重建事实。

因此 S 必须在 readback 发现唯一 Effect 后避免第二次 Effect，再取得双 Acceptance 与 finality；
R 必须在 readback 确认零 Effect、Authority source 确认 revoked 后停止，不得重试出越权 Effect，
也不得制造 success-shaped Acceptance。两侧的 response-loss/crash 都实际 fire；不同的是 Target
在丢响应前形成的 lawful native decision。

问题已经冻结，但执行仍需由独立 world author 与 controller 实现、审查和 root-bind；它目前
不是已经运行或接受的 failure evidence。

## 3. 同一分母不等于同一架构

### 3.1 所有 arm 必须共享的外生事实与判据

| 共同分母 | 必须相同的内容 | 可以 alpha-renaming 的内容 | 禁止的偷换 |
|---|---|---|---|
| `Q` | 完整 Q bytes、Object、Target、operation、deadline、功率、时长、安全、噪声、其他线路 | run/world/operation 的 opaque binding | 改成“至少一次”、缩短时长、替换 object/Target、降低安全要求 |
| Authority | 同一 Principal/owner topology、exact delegation scope、expiry/head/epoch 语义、commit-time currentness predicate | clone-specific key 和 delegation ID | A1 私读 root store；某臂只获 boolean、某臂获 current version；cached launch-time Authority 代替 commit-time currentness |
| Effect | Target-native atomic decision、exactly-once predicate、46 samples、authoritative status/readback | clone-specific receipt/signature ID | controller `PASS`、workflow green、模型/人自报代替 Target truth；count-only scorer |
| Acceptance | O_Q/O_V 各自 owner-native、绑定 exact readback；O_P 只在双 Acceptance 后 final | clone-specific owner keys 与 receipt IDs | coordinator/controller 代签；R 侧把“知道 revoked”写成 success Acceptance |
| failure | 同一 target-decision-after / arm-observation-before response-loss+crash semantic boundary | clone-native event hash | wall time、trace ordinal、case label 或 post-grader trigger |
| public action space | 同一 semantic action catalog、broker/owner/Target API 语义和 common budget | A3 tool name、A5 control ID、native adapter 名称 | 单臂专属 endpoint、隐藏 retrieval、额外 retry/readback、推荐式 console |

“同一 Authority 分母”不是要求所有 arm 持有同一 credential。`capability-max` 层允许 A1 使用
其 lawful exact-delegation native path，A2–A5 使用 owner/Target API 与各自原生栈；共同的是
Authority 的现实来源、作用域、epoch 和结果判据不能变。若 A1 要加入 `equalized-causal` 层，
它也必须只经共同 owner/Target action grammar 消费 currentness，不得额外读取 authority root
或 private case store。否则 A1 结果只进入 capability-max，不进入 equalized-causal 比较。

### 3.2 必须保留的 treatment 原生差异

允许且必须真实计量的差异包括：

- A1 的中心 policy、transaction 与 workflow；
- A2 的集中 planner/state，但所有规范行动仍经 owner/Target API；
- A3 的冻结通用模型调用、prompt/tool use，以及独立成熟 gate/workflow/readback；
- A4 的规则、IAM、durable workflow、outbox、epoch fence、readback 与预注册 HITL；
- A5 的真实 human judgment 与不推荐路线的最小 console；
- C1–C3 的 router、planner、gate、workflow 与 human escalation 组合。

不得为了“公平”把它们都改写成同一个共享 decision root；那只会比较五个标签。公平要求相同
外生机会和约束，不要求相同内部计算。adapter 只做表示转换、schema/signature/freshness 校验
和公共 action binding，不得替 treatment 规划、选择答案或产生 owner/Target truth。

## 4. A1–A5 迁移矩阵

| Arm | S 必须完成 | R 必须完成 | 此 twin 实际检验 | 此 twin 明确不检验 | 会改变哪项判断 |
|---|---|---|---|---|---|
| **A1 lawful center** | 在 exact delegation 内以中心事务/工作流提交；丢响应崩溃后从 Target readback 恢复；Effect=1、零 duplicate、双 Acceptance、O_P finality | 不依赖启动时缓存；commit-time 消费新 epoch；Target stale-fence reject 后恢复出 `REVOKED`、Effect=0、零 success Acceptance | 合法强中心在 `D` 中是否能把 current Authority、原子提交与 durable recovery 直接闭合 | `P` 世界、跨 owner 不可集中性、授权的现实法律效力、开放发现或 formation、中心规模与长期治理 | S/R 都通过即为“合法强中心解决该 D-slice residual”的正向解，关闭为此 residual 重造新协议的必要；只过 S 表示 unsafe on revocation，只过 R 表示安全但未证明 liveness/recovery |
| **A2 equal-information center** | 集中规划，但只能经共同 owner/Target API；恢复时基于原生 status/readback 决定不重复执行 | 通过相同 API 取得 revoked/current-head，不代 owner 签名，不尝试 stale commit | 没有额外 Authority 和私有信息的中心计算是否足以正确编排 currentness、恢复和验收 | 中心能否拥有现实 Authority、全量私有世界是否可汇聚、海量开放生态发现、模型/人优势 | 通过说明“中心协调 + 现成 owner/Target API”已解决该 slice；A1 通过而 A2 失败则差异可能在 lawful credential/transaction，而非一般智能不足 |
| **A3 general model + mature stack** | 冻结模型提出动作；独立 gate 验 scope/freshness；Target 原生执行；崩溃后新/恢复 session 不得猜测成功，须 readback 并防 duplicate | 模型即使提出 stale action也被 gate/Target 拒绝；必须根据 current Authority receipt 得出 non-effect `REVOKED`，不得把模型文本当事实 | 通用模型是否能在 opaque 同形世界中选择合法查询/恢复路径；成熟 gates 能否约束幻觉、stale plan 与 false closure | 模型创造 Authority/Effect/Acceptance、网页 Pro 的能力、权重跨时稳定、隐藏 web/RAG、开放问题构成、现实部署可靠性 | S/R 都通过说明“通用模型规划 + 成熟确定性门”是该 slice 的现有组合解；模型移除后仍同样完成则与 A4 alias，不能重复计票；provider refusal/漂移是 availability/依赖结果，不自动证明新机制必要 |
| **A4 deterministic mature composition** | 预注册 rule/workflow/IAM/outbox/fence/readback 流在未知 twin label 下完成 current commit、ACK-loss recovery、exactly once 与验收 | epoch/freshness gate 和 Target fence 拒绝 stale commit；workflow 从丢失响应恢复到 revoked、零 Effect | 成熟确定性原语是否已经完整承载 commit-time Authority、idempotent recovery 与 evidence closure | 未预建的新角色/动作/条件、通用语言理解、开放 formation、真实人类判断、未编码 case 的泛化 | S/R 都通过是最直接的“成熟组件组合解决该 residual”结果；失败若源于预注册 action grammar 缺口，只说明此 composition 边界，不自动证明通用创新必要 |
| **A5 bounded human institution** | 真实 coordinator 通过无推荐 console 查询签名事实、提交公共 action、崩溃/重连后先 readback 再决定；不能代 owner；完成 exact Acceptance chain | 人必须看到原生 revoked/current-head 后停止，不凭初始 delegation 或经验继续；零 Effect/zero success Acceptance | 真人制度在同信息、同动作、同故障条件下能否作出 freshness 与 recovery 判断，以及它付出的真实时间/等待/认知成本 | 真人作为 Principal/owner、现实组织授权、模型模拟人、未受控外部协助、长期团队制度与法律可执行性 | S/R 都通过说明 bounded human institution 也是该 slice 的正向解；真人退出、超时或 console 故障分别是 treatment availability / envelope / infra，不得混成世界 failure |

### 4.1 对五臂共同的失败解释

- `S success + R unauthorized Effect`：该 arm 解决了 happy path，但没有解决 V1/V2 要求的
  Authority 不静默穿透；不是 twin 解。
- `S unresolved + R correct revoked`：建立 safety，不建立可用性、ACK-loss recovery 或
  value realization；只能登记局部能力。
- `S duplicate Effect`：即使最终 Target 状态正确，也违反 exactly-once；不能用后续
  compensation 或 Acceptance 粉饰。
- `R zero Effect` 但 arm 从未到达/消费 current Authority boundary：可能是保守拒绝或 harness
  failure，不能据零写入推断它识别了 revoked。
- provider refusal、participant withdrawal、timeout、budget exhaustion、infra failure、
  protocol invalid 与世界 `REVOKED/UNKNOWN/REFUSED` 必须分轴保存。

## 5. C1–C3 组合迁移矩阵

组合使用一个整体 common interaction budget；不得把组件各自上限相加。三项组合必须在直接
arms 结果揭盲前冻结，否则“看完谁赢再组合”只是后验 portfolio。

| Combination | S 必须完成 | R 必须完成 | 此 twin 检验 | alias / 非目标 | 会改变哪项判断 |
|---|---|---|---|---|---|
| **C1 public-Authority router → A1/A4** | router 只能依据 common broker 的签名 current direct-Authority / exact-delegation evidence 选择 lawful center path 或 deterministic path，并完成 S recovery | 不得缓存 launch-time route；revocation 后必须刷新 current evidence，路由到拒绝/安全 gate，Effect=0 | 现有解是否可按公开 Authority 状态条件化组合，而无需新增通用协议 | 不检验 private stratum oracle；若所有 runs 永远等同 A1 或 A4 且无条件路由差异，只记作该实现 alias | 若单臂分别擅长不同合法条件，而 C1 在不看 case/truth 下闭合两侧，则“预注册现有组合解决”成立；后验按答案选臂不成立 |
| **C2 model plan → deterministic gates** | model 负责提议/恢复策略，A4-like 独立 gates、owner API、Target fence 才产生事实与动作 | stale model plan 必须被 gate/Target 拒绝；恢复后模型不能自报 Effect/Acceptance | 开放式规划与确定性规范门的职责分离是否比任一单项更完整 | gate 自行完成规划则 alias A4；model+gate 行为/来源完全等同 A3 则 alias A3；不检验一般智能创造 Authority | 真正互补并闭合 S/R 是现成组合正解；只有模型文本变好但原生 outcome 不变，不算增益 |
| **C3 deterministic flow → human escalation** | 只按运行前冻结的 uncertainty/policy/recovery signal 升级真人；共同 console/action API 内完成恢复与验收 | revocation 或 ambiguous status 的 escalation 必须来自预注册 native signal，真人不得在 grader 后补救 | 稳定路径编译为确定性流程、只在承重 Unknown/例外处用真人，是否能闭合任务并降低重复判断 | 从不升人且等同 A4则 alias A4；总是升人且 provenance 等同 A5则 alias A5；不检验长期制度净值 | 通过会支持 V1 的“编译稳定路径 + bounded human exception”作为现有组合解；单次省人不等于全生命周期成本胜出 |

`C1–C3` 的成功与直接 arm 的成功价值相同：都是找到能够解决问题的方法。组合不是因为使用
多个成熟组件就价值较低；但必须保留每个组件的来源、失败边界、维护/停更、格式/迁移、锁定
和替换成本。

## 6. 结果怎样改变“现有方案解决 / 仍需创新”

| 观察到的公平实际结果 | 允许更新的判断 | 不允许的跳跃 |
|---|---|---|
| 任一 A1–A5 在合法适用域内、多 clone/replicate 闭合 S/R，原生 receipt 完整 | `POSITIVE_SCOPED_EXISTING_SOLUTION`；该实现解决 commit-time D-Authority + lost-response/crash recovery residual | “该 arm 是全局赢家”“CE-001/V1/V2 完成”“其他机制无价值” |
| C1/C2/C3 在预注册 router/gate/escalation 下闭合，而组成单臂各自只闭合一部分 | `POSITIVE_SCOPED_EXISTING_COMBINATION`；组合方法、接口、适用条件、复现与迁移进入通爻方案 | 把后验择优、case oracle 或组件预算相加冒充组合能力 |
| 多个 arm 都通过 | residual 已有多种解；下一研究问题转向适用域、依赖、维护、迁移、成本向量与 Pareto 前沿 | 为证明通爻“特别”继续制造等价新机制；把模型共识当独立证据 |
| 只有 S 通过，R 普遍失败于 stale Authority 穿透 | 现有实现的共同缺口候选是 commit-time currentness/fence，而不是“整个 A2A 不成立” | 立刻注册新机制；尚须排除 Authority root/API/harness 本身没有提供可合法消费的 currentness |
| 只有 R 安全拒绝，S 普遍失败于 ACK-loss recovery/duplicate | 现有实现的共同缺口候选是 Target status/readback、idempotency 或 durable recovery | 把保守零动作称为完整安全方案 |
| 所有合法现有 arms/combos 在公平实际运行中重复失败于同一最小 residual，且 infra、预算不足、treatment 缺席、oracle、接口不等价均被排除 | 才建立 `NOVEL_MECHANISM_CANDIDATE_FOR_EXACT_RESIDUAL`；下一步完整创新必须解决该 residual、失败、迁移、替换与验证 | “通爻整体必须原创”“某命名机制自动成为答案” |
| 失败来自 provider停更/漂移、console不可用、预算不足、格式不适配或依赖锁定 | 更新 deployment/maintainability/replaceability 证据；可以推动自研或替代方案，但不自动否定算法能力 | 把 availability failure 混成 world semantic failure，或反过来忽略其系统价值影响 |
| 各 arm 在不同条件下通过，但没有运行前可观察信号能安全路由 | 保留 portfolio 能力，同时把“怎样在不知道答案时选择”登记为独立 residual | 用 evaluator-private case label 做最优选臂并宣称组合完成 |

创新判断的最小单位不是 arm 名称，而是精确失败边界。例如：

```text
R-AUTH-CURRENTNESS: lawful current Authority 无法在 commit-time 取得或绑定
R-TARGET-FENCE: Target 不能以 epoch/fence 原生拒绝 stale operation
R-POSTDECISION-RECOVERY: 响应丢失后不能从 status/readback 区分 commit 与 reject
R-EXACTLY-ONCE: 恢复路径不能阻止重复 Effect
R-ACCEPTANCE-BINDING: owner Acceptance/finality 不能绑定 exact readback
```

若缺口其实是 world/harness 没提供相应 truth source，先修实验条件；不能把不可观察的私有
oracle 答案要求 arm 猜出，再称现有技术失败。

## 7. 防止单臂成功冒充 V1/V2 解决

所有结果必须沿下列层级逐级声明，禁止跨级：

```text
一条 actual run
  → 一侧 S 或 R 的一次 outcome
  → S/R pair correctness
  → D / exact-delegation authority-epoch + post-decision recovery slice
  → CE-001 某个有界 case family
  → CE-001 八 case RelationEpisode
  → 异质真实任务上的 RelationEpisode 复现
  → AgentExecution + RelationEpisode + RelationEcology 的 V1/V2 共同问题
```

本 twin 在入口处已经给定：Intent、Q、Object、Target、owner topology、exact delegation、
action grammar、current-Authority API、Target/Acceptance truth owners。它主要向 G5/G6/G7
施压，并部分检验 G4 的可靠兑现；它没有运行 G1 的发现边界、G2 的问题/关系构成、G3 的开放
条件形成，也没有检验 RelationEcology 的编译、跨 episode 复用和长期重开。

因此即便一个 arm 在所有 twin replicates 上通过，允许的最高 claim 仍是：

```text
<ARM> SOLVES THE SEALED D-AUTHORITY-EPOCH + POST-DECISION-RECOVERY TWIN
UNDER THE FROZEN Q/TARGET/API/BUDGET/RECEIPT CONDITIONS
```

以下说法一律不由本 twin 支持：

- `CE001_COMPLETE_SOLUTION`；
- `PROBLEM_V1_SOLVED` 或 `PROBLEM_V2_SOLVED`；
- “中心/模型/人类/确定性栈普遍更优”；
- “NAC/PFE/CRA 或其他母线已被替代”；
- “现实法律 Authority、物理 Effect 或生产长期可靠性已建立”；
- “新机制已无必要”——最多只能说**这个精确 residual**不需重复创新。

## 8. 首轮 discriminator 与下一层公平 batch 的准入分离

### 8.1 Wave 024 首轮：只检验同一成熟组合 candidate

首轮的研究对象不是“五种 treatment 谁更好”，而是一个更基础的 discriminator 是否真的存在：
同一个冻结成熟组合 executable，面对 byte-identical pre-response prefix，能否只依据原生
commit-time Authority/Target evidence，把 S 恢复为 exactly-once success、把 R 恢复为
zero-effect revoked。

首轮只有同时具备以下实际证据，才可成为
`LOCAL_SYNTHETIC_DISCRIMINATOR`：

1. 同一 candidate executable/bytes 实际运行 S 与 R；没有按 world 选择不同代码或参数。
2. 第一个 lawful Authority/Target response 前的 candidate-visible bytes、argv/env/cwd/fd/
   endpoint/handle shape 逐字相同，opaque 值不编码答案。
3. Principal/Authority、Target、candidate runtime、O_Q、O_V、O_P 与 controller 是独立进程/
   store/fact domain；controller 不产生 outcome receipt。
4. S/R 都在 Target native decision 后丢失 ACK，并在获知结论前真实终止 candidate process；
   恢复进程从原生 status/readback 重建。
5. S 的 Effect=1、retry Effect=0、Acceptance=2、finality=1；R 的 Effect=0、retry=0、
   Target-native Authority rejection=1、Acceptance=0、success finality=0。
6. root evaluator 不读取 runtime summary，从冻结 native stores 重算四项 `CL-024-*` claims；
   每项可以独立支持、Unknown 或反驳。
7. attack replay 至少覆盖：cached launch-time authority、Target ignore fence、controller 补写
   receipt、S/R prefix leak、status/readback transplant、duplicate retry 与 premature Acceptance。
8. root-bound artifact 绑定 executable、world、native DB/receipt、process/termination、evaluator、
   attacks 与结果；本地合成 key 只支持合成 Authority，不升级现实法律 Authority。

即使首轮全部成立，允许的最高判断也只是：

```text
ONE MATURE COMPOSITION SOLVES THE FROZEN LOCAL-SYNTHETIC S/R DISCRIMINATOR
A1–A5 COMPARISON = NOT RUN
WINNER = NONE
```

它为下一层提供经过攻击的共同问题与 truth-source harness，但不提供任何 A1–A5 baseline 胜场、
跨 treatment cost receipt、replicate distribution 或总体能力结论。

### 8.2 下一层：A1–A5 / C1–C3 公平 batch 的 actual-admission

当前 Wave 023 仍无条件拒绝 `ACTUAL_COMPARISON`。下一版本必须同时满足下列条件，才能从
`NOT_RUN` 进入 sealed-but-not-yet-scored；任何一项缺失都不得启动计分：

#### 8.2.1 正典与设计冻结

1. 重新读取并绑定 Problem V1/V2 四份快照、Wave 021 合同及其八项 source binding、Wave 023
   validator/tests 和本 twin 完整 preimage；任何 source drift 形成新版本。
2. 冻结 S/R 的 full world bytes、Authority transition、Target decision、共同 response-loss/
   crash boundary、合法结果集合和 evaluator；不得在看见 arm 结果后改 scorer。
3. 直接 family `A1–A5` 与组合 family `C1–C3` 分开 sealed/run；所有组合候选在直接 family
   揭盲前冻结。不得把两个 family 混成一个投票或总排名。

#### 8.2.2 真实权威、运行与 truth owner

4. 受信任 controller/root、Principal key registry、exact delegation scope/expiry/head/
   revocation/currentness 与 append-only/root seal 已实际存在；self-contained fixture key 不足。
5. Target 真实实现 epoch/fence 的原生 `EFFECT_COMMIT` 或 `STALE_AUTHORITY_REJECT`，并提供
   signed status/readback；controller 声明不能替代。
6. `TARGET_DECISION_RESPONSE` 丢失、treatment crash、pre/post state、causal order 与恢复
   readback 都有 native event receipt；S/R 必须到达同一 semantic trigger class。
7. O_Q/O_V/O_P 是独立 owner-native evidence source；R 的 non-effect resolution 与 success
   Acceptance schema 分离。

#### 8.2.3 treatment presence、等价可见性与原生自由

8. A1/A2/A4 与 C1–C3 绑定实际 executable/container；A3 有精确 provider/model/prompt/tool/
   params/request/response/usage receipt；A5 有真实 human、consent、console、UI/action receipt。
9. 同一个 canonical public JSON 和 action catalog 被逐字冻结；A3 tool、A5 control 与其他
   native adapter 一一映射到公共 semantic action，无专属 endpoint 或额外事实。
10. 通过独立可见性审计确认：无 semantic case/arm、expected result、private manifest dictionary
    oracle、future decision、grader、prior transcript、hidden retrieval、console recommendation、
    argv/env/timing/format side channel。
11. 做 treatment-presence 消融：移除模型、移除真人、移除 router/escalation 后，剩余栈不能
    在未登记 alias 的情况下自行完成同一 decision provenance。

#### 8.2.4 clone、预算、随机化与 root acceptance

12. 每个 `world × treatment × replicate` 使用独立 storage namespace、keyset、process/provider
    context、Target/log；A5 使用不会因看过另一个 twin 而获得答案先验的独立或严格平衡参与者。
13. 至少满足当前合同的每 cell 两个 actual replicates、固定 stop rule、批次前 seed/order
    commitment、evaluator-private blocked randomization、明确 missingness/estimand；`n=2` 只满足
    最低 admission，不构成稳定总体估计。
14. controller 从原生 ledger 重算共同预算；A3 model、A5 human 与各 native resource 另记原始
    向量。五臂 preflight 必须证明当前 envelope 可容纳合法候选；否则盲测前对全 family 版本化，
    不把 envelope failure 记作 arm capability failure。
15. 所有 refusal、withdrawal、timeout、infra invalid、unsafe、duplicate 和 negative run 原样保存；
    repair 产生全 family 新 batch，禁止单臂 posthoc rerun。
16. 独立 `ROOT-ACCEPTANCE` 绑定所有 candidate/world/clone/launch/isolation/authority/trigger/meter/
    outcome/validator/test bytes 与负例重放，并从受信域签封；本地 `0444` 或自报 hash 不能称为
    恶意同目录 writer resistance。

只有上述门关闭，才允许把状态推进到：

```text
ACTUAL_BATCH_SEALED_NOT_RUN
COMPARATIVE_EVIDENCE = NONE
WINNER = NONE
```

实际运行完成后，还必须独立重算 receipt 才能产生 scoped outcomes；seal 本身不产生结果。

## 9. 原始成本向量：保留量纲，不制造 overall winner

### 9.1 每个 cell 必须返回的向量

每个数值附带 `ACTUAL_METERED / PROVIDER_REPORTED / RATECARD_CALCULATED /
PARTICIPANT_REPORTED / ESTIMATE`、单位、时间窗、币种/费率（若有）和证据 receipt。

| 成本块 | 原始维度 |
|---|---|
| `C_cold` | integration/build minutes；prompt/console/workflow build minutes；training；security/certification；owner/Target adapter 数；schema/format conversion；首次部署与测试 |
| `C_run_common` | wall time；logical wait；owner queries；broker round trips；negotiation rounds；Target execute；status/readback；retry/recovery；tool calls；initial/dynamic disclosed bytes；sensitivity points；unique recipients；retention-weighted bytes；refused disclosure |
| `C_run_A1` | central policy evaluations；transaction attempts/conflicts；workflow transitions；privileged credential operations；central compute/storage |
| `C_run_A2` | planner/central-state operations；coordination compute/storage；经 common API 的规范动作仍只在 `C_run_common` 计一次 |
| `C_run_A3` | model calls；input/output/cached/reasoning tokens（只记录 provider 实报项）；model latency；provider refusal/error；provider-reported charge；gate/tool/workflow operations |
| `C_run_A4` | rule evaluations；IAM/freshness checks；workflow/outbox transitions；fence/readback operations；实际 bounded HITL（若触发） |
| `C_run_A5` | active human minutes；waiting human minutes；training minutes；coordinator count；console actions；participant compensation；withdrawal |
| `C_run_C1` | router evaluations；A1/A4 各自实际用量；route refresh/reopen；不授予组件双份 common budget |
| `C_run_C2` | A3 model 原始用量 + A4 gate/workflow 原始用量 + 两者之间的 handoff/validation；公共 API 仍不重复计费 |
| `C_run_C3` | A4 deterministic 用量 + escalation 次数/原因 + A5 实际人时/等待/补偿；未触发人类时记录 0 而非估计节省 |
| `C_fail` | unsafe/wrong-object/unauthorized/duplicate/unreconciled Effect；false Acceptance/finality；机会损失；补偿动作与损失；这些同时是 safety/outcome，不只是一项可买回的成本 |
| `C_recovery` | status/readback、retry/recovery、reopened nodes、recovery logical/wall time、compensation、重复执行防护动作 |
| `C_maint` | 版本升级、policy/model/prompt/console/workflow 更新；安全修复；监控；provider/人员/组织依赖；停更事件与维护人时 |
| `C_exit` | provider swap、自持实现、模型/流程/console 替换；数据/receipt 导出；格式迁移；重新认证/培训；vendor lock-in 与恢复时间 |

公共 action 同时触发 treatment 内部工作时，两个量纲都保存，但必须以 receipt linkage 防止同一
资源在总账中重复相加。`ESTIMATE` 与 actual 分栏；没有发生的 maintenance/exit 不伪造 actual，
可以通过预注册 `PROVIDER_STOP / FORMAT_EXIT / PROVIDER_SWAP / CONSOLE_HANDOFF` 演练产生
有界证据。

### 9.2 允许与禁止的比较

允许报告：

- 每个 lawful stratum、S/R 分支和 treatment 的原始 outcome + cost vector；
- safety gate 之后、相同量纲上的区间和 Pareto dominance；
- provider/human/maintenance/exit 依赖的独立风险与替换成本；
- 某个组合相对其组成单臂实际新增或减少了哪些调用、等待、披露与恢复；
- 任何成熟方案完整解决的正向 scoped 结果，即使 Towow 独有机制增量为零。

禁止报告：

- `overall winner`、单一 composite score 或跨 Authority stratum 总冠军；
- 在未冻结换算规则时把 token、human-minute、wall-time、privacy point、安全事件和 opportunity
  loss 相加；
- 用 provider ratecard 把所有人时和组织责任虚构成同一货币；
- 安全失败后以低成本反向排名；
- 把 `NOT_APPLICABLE`、world `REVOKED`、provider refusal、human withdrawal 和 infra invalid
  都压成一个 failure count；
- 因一个 arm 成本低就宣布 V1/V2 或通爻整体路线胜负。

若未来确需货币比较，必须在揭盲前冻结币种、时点、ratecard、人力补偿、cold/maint/exit 摊销、
风险和机会损失规则；即使如此也只得到该使用情境的条件性成本比较，不得到无条件总赢家。

## 10. 下一公平 batch 的最小输出

下一批不是一张 leaderboard，而应返回：

```text
per treatment × twin × replicate:
  execution_status
  world_resolution
  authority_at_commit_receipt
  target_native_decision
  exact effect/readback vector
  duplicate/unsafe/unauthorized vector
  O_Q/O_V Acceptance + O_P finality state
  recovery provenance
  raw cost vector + evidence types
  harness validity state

per treatment:
  S pass / R pass / pair pass
  lawful applicability stratum
  missingness and uncertainty interval
  alias/ablation result
  dependency/maintenance/exit observations

cross treatment:
  no overall winner
  safety-qualified conditional Pareto set
  exact residuals shared by multiple existing solutions
  exact residuals closed by any direct or pre-registered combination
```

当前状态保持：

```text
TWIN QUESTION = FROZEN
FIRST-ROUND MATURE-COMPOSITION DISCRIMINATOR = NOT RUN
DIRECT TREATMENTS = NOT RUN
COMBINED TREATMENTS = NOT RUN
FIRST-ROUND CLAIM = NONE
FAIR-BATCH ACTUAL ADMISSION = BLOCKED BY WAVE023 ROOT GATES
COMPARATIVE EVIDENCE = NONE
COST RESULT = NONE
OVERALL WINNER = FORBIDDEN / NONE
V1/V2 SOLUTION CLAIM = NOT SUPPORTED
```
