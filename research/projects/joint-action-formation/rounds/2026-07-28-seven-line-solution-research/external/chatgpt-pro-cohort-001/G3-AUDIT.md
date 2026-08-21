# ChatGPT Pro G3 独立敌对审计

日期：2026-07-29  
状态：`INDEPENDENT AUDIT / REVISE BEFORE EXPERIMENT / NO FORMAL STATUS CHANGE`

## 审计对象、证据边界与总判断

本审计只使用本地已保存材料：

- [`G3-return.md`](./G3-return.md)；
- [`G3-final.md`](../codex-cli-cohort-001/G3-final.md)；
- [`Wave010 X1 outcome-contract v1 candidate`](../../experiments/wave-010-x1-outcome-contract-v1/README.md)
  及其 validator/test；
- 当前正式入口 `research/NOW.md`、本轮 `PROGRAM.md` 和既有 G3 设计/合成。

未联网核验 Pro 返回中的网页来源标签。其转录只保存可见正文，没有保存逐主张 URL、引用位置、
原始返回字节或 source mapping。因此本审计不把 OPA、Temporal、Camunda、NIH、Nadcap、
GitHub、AWS 或 2026 planner benchmark 等外部技术叙述登记为已核实事实。

总判断：`REVISE_BEFORE_EXPERIMENT`。

Pro 返回不是简单地把 G3 全部偷换成普通 planning；它明确识别了 planner、workflow、强中心、
人类流程和成熟组合可能完整解决，也明确承认形成动作进入完备 action model 后，搜索部分就是
普通规划。真正的问题是它同时使用了两个不同的“不可达”：

1. `S0` 中没有**立即执行原任务**的路径；
2. `S0` 中没有包含 ask/probe/sign/build/permission/partner 等前缀的**完整合格 policy**。

Pro 的 `NEWLY_QUALIFIED` 主要建立在第 1 个量词上；本地 G3/X1 合同的 `C=UNSAT` 建立在第
2 个量词上。二者不等价。若不修订，实验会把
`C=SAT, N=NEW_TOKEN, E=SAME, T=INVARIANT, V=VALID`
这种“旧 policy 产生新现实 token”的普通闭包正例，误写成“原闭包从不可达变成可达”。

## 一、逐项判定

| 返回中的主张或设计 | 审计标签 | 判断 |
|---|---|---|
| 现有 planner、workflow、IAM、人类流程、强中心或组合完整解决时就是正向结果 | `VERIFIED` | 与 `PROGRAM.md`、NOW 的 solution-first 边界及本地 G3 一致；没有预设通爻独特性或新协议必要性 |
| model absence、actual absence、discovery、restoration、new token、task fork、Authority substitution 应分开 | `VERIFIED` | 这是必要区分，并与本地 `C/N/E/T/V` 多轴表示方向一致 |
| owner 正式改变目标/底线得到 `AUTHORIZED_NEW_EPISODE`，不能冒充原 Episode 成功 | `VERIFIED` | 与 X1 v1 的独立类别、精确 task diff 和 owner receipt 要求方向一致 |
| 私有意愿、产能和批准不能作为免费、必答、永远正确的 oracle | `VERIFIED_AS_DESIGN_CONSTRAINT` | Pro 多处明确禁止；是否在其拟议 evaluator 中真正封住仍未运行 |
| “当前执行路径”与“条件形成轨迹”分层可表达现实 token 首次出现 | `PLAUSIBLE` | 可作为 `N=NEW_TOKEN` 的现实事件描述；不能单独支撑 `C=UNSAT` 或新 formation method |
| 封闭、已知动作模型、合法集中控制下，成熟组合会解决搜索和执行 | `PLAUSIBLE` | 有构造合理性；当前本地仅有有限合成 QHM-1，不是现实 full-stack 或真人制度验证 |
| “G3 真正研究的是让当前执行路径从空集变非空” | `OVERSTRONG` | 静默缩窄了正式 G3：诊断、actual-policy miss、bounded unreachable、合法 Refuse/Defer/Unknown 和 safe exit 也属于母线结果 |
| `Π_E(W_t0)=∅` 足以作为 formation 的前态空集 | `OVERSTRONG` | 其 `Π_E` 只枚举 `A_T*`，排除了形成动作；它证明无直接执行路径，不证明 full-policy closure 无解 |
| 成熟组件“基本已经解决”三个领域中的完整 G3 | `OVERSTRONG` | 组件责任清单与任务叙述不能替代同一冻结 episode、同权限、同成本、同 verifier 的端到端运行 |
| `CERTIFIED_EMPTY` 可由 `B/H + 足够完整 authoritative state` 判定 | `UNRESOLVED` | 未冻结完整 action/meta-action、partner/tool/representation、response、observation、transition 和 human-creation inventory |
| formation witness 与 causal removal 能证明路径首次由干预创造 | `UNRESOLVED` | 没有封住 treatment 后选择 operator、注入最终 evidence、用 hidden truth 重规划或不一致删除派生效应的 oracle |
| 三域 216 episode benchmark 能给出可信 residual | `UNRESOLVED` | 在小型量词、inventory、baseline 和 causal evaluator 验证前，扩大任务皮肤只会复制未解决的判定歧义 |
| 返回中的外部技术与政策事实 | `UNRESOLVED_SOURCE` | 当前 bundle 没有可重建的逐主张官方文档/原始论文映射 |

## 二、最强反例：`NEW_TOKEN` 不等于旧闭包 `UNSAT`

构造一个冻结 Episode：

- `Q` 要求由独立 Authority holder 签发当前 scope 的 purpose token 后执行任务；
- `S0` 中 token 不存在，因此没有仅由 task-execution actions 构成的立即执行路径；
- 旧 action/meta-action model 已包含 `request(holder) → sign(holder) → execute`；
- response family、holder policy、预算、horizon 和 transition semantics 均在运行前冻结；
- controller 不能代签，holder 可批准或拒绝；
- 该 policy 只依赖合法 observation history。

若 holder 在 actual branch 合法签发 token 并完成 Effect，则：

```text
Pro 的直接执行路径集合：Π_exec(S0)=∅
full-policy closure：C=SAT
operative delta：N=NEW_TOKEN
kernel delta：E=SAME
task：T=INVARIANT
trace：V=VALID
```

这同时证明两件事：

1. 一个真实、Authority-bound 的新条件确实在 Episode 内形成；
2. 旧冻结 policy closure 从一开始已经可达，形成方法没有创造新的规划可达性。

Pro 在结尾承认“形成动作进入完备 action model 后就是扩展动作集上的规划和执行”，但其核心
定义又要求“实际 S0 无合格执行路径”并把后态称为 `NEWLY_QUALIFIED`。若 evaluator 只检查
`Π_exec(S0)=∅`，上述普通 prefix-SAT world 会成为 formation 真阳性；若把它解释成
FORM-REACHABILITY 的 `UNSAT→SAT`，结论就是假的。

因此应保留现实事件 `N=NEW_TOKEN`，撤销任何从该事件直接推出旧 closure `UNSAT`、需要新
planner 或产生新方法增量的推理。

## 三、inventory 完整性审计

Pro 的 Episode 定义冻结 `I/Q/V0/P*/A*/B/H/ν`，这是必要但不充分的。`B` 只是文字化世界
边界，不等于可执行、可穷举、可哈希绑定的完整 inventory。

| inventory | Pro 当前是否冻结 | 主要缺口 |
|---|---|---|
| capability | `PARTIAL` | 列出现有能力和形成动作类型；未冻结 capability acquisition language、等价规则、版本与执行语义 |
| Authority | `PARTIAL` | 冻结所需关系，但“Authority topology 不变”和“新权限/授权形成”之间没有拆开 topology、locus、Mandate 与 token state |
| tool | `NO` | 采购/部署工具是候选动作，但没有有限工具集合、build/install DSL、验证器或开放 inventory 标志 |
| partner | `NO` | 必要 Principal 与可替换角色被描述；市场、供应商、潜在伙伴和新关系候选空间没有 completeness receipt |
| task representation | `NO` | 允许制度性/接口性重表示，却没有冻结可允许 transformation、语义等价 checker、model diff 或任意程序边界 |
| exit | `PARTIAL` | 有 `UNKNOWN/REFUSED` 叙述；没有冻结 Refuse/Defer/Unknown terminal、safe/terminal robustness、过度 abstention 和循环语义 |
| observation/response | `PARTIAL` | 查询字段较完整；未把 observation kernel、allowed response family 和 after-the-fact shrink 防护写成必需 receipt |
| transition/search | `NO` | 没有 executable transition fingerprint、完整 meta-action set、search bound 和 unresolved-items 机器约束 |

这直接限制三类结论：

- `CERTIFIED_EMPTY` 只有在 X1 v1 所要求的 action inventory、response family、observation
  kernel、transition semantics 全部 `COMPLETE`，search bound 冻结，并得到
  `C=UNSAT / R_physical_exists=FALSE / R_measurable_exists=FALSE` 时才可登记；
- partner、tool、representation、人类创造或任意 program semantics 任一开放时，只能是
  `UNKNOWN/UNRESOLVED_MODEL`，有限搜索耗尽不是 bounded unreachable；
- “S0 实际没有路径”不能由领域专家在看到成功轨迹后口头确认，它需要运行前冻结的可执行
  inventory 和独立 closure oracle。

## 四、actual-policy miss 与 bounded unreachable 尚未严格分开

Pro 的五类结果没有独立的 `ACTUAL_POLICY_MISS` 或 `BOUNDED_UNREACHABLE`。它把前者放在
failure mode 中，主要解释为 stale policy、错误 IAM 状态、错误 Authority 或非权威摘要；把
后者近似写成 `CERTIFIED_EMPTY`。

这与 X1 v1 的机器语义不相容：

```text
ACTUAL_POLICY_MISS
  requires C=SAT
  and R_physical_exists=TRUE
  and R_measurable_exists=TRUE
  and R_actual=FALSE

BOUNDED_UNREACHABLE
  requires C=UNSAT
  and R_physical_exists=FALSE
  and R_measurable_exists=FALSE
  and frozen search bound
  and COMPLETE action/response/observation/transition inventory
```

使用过期政策或错误 source of truth 首先是 model/state/evidence invalidity；只有另有独立 oracle
证明合法 measurable policy 存在而 actual method 失败时，它才同时构成 actual-policy miss。
反过来，某个 arm 没找到 plan，无论运行多久，都不能成为 bounded unreachable。

本地 X1 v1 的 6 项 conformance test 当前通过，但其状态仍是
`CANDIDATE_NOT_RUN / NO X1 RUN`。这只证明上述分类约束在测试 fixture 上可执行，不证明 Pro
拟议 benchmark、任何方法或现实 episode 已满足。

## 五、formation witness 与 causal-removal 的 post-treatment oracle

Pro 提议由 domain owner、Authority holder、独立评审和 red team 建立 sealed truth，并在成功
后运行 sufficiency、minimality、remove/reverse/block。方向正确，但以下五条尚未被封住：

1. **事后选择 treatment。** 看到成功 trace 后才挑选“关键”干预集合 `D`，再让 evaluator
   验证它，容易把结果相关对象包装成预先假说。
2. **事后扩展等价类。** 看到最终 token、adapter 或关系后才决定什么算等价旧对象，会双向
   制造“新”或“早已存在”。
3. **不一致删除。** 删除 token 却保留由它产生的知识、reservation、权限、信任、部署或
   target state，会伪造非必要；连同所有后果一并删除但不恢复共同外生条件，又会伪造必要。
4. **全知重规划泄漏。** removal evaluator 若读取 hidden willingness、最终 proposal、最终
   receipt 或真实 branch，再从 reset world 求解，它测到的是 hindsight oracle，不是合法
   observation policy。
5. **作者同源自证。** world author 同时定义 hidden truth、SCM、qualified predicate 和
   intervention effect，再对同一生成机制评分，只能证明 fixture 内部一致。

进入评分前至少必须冻结并由 runner 持有：

- exact `S0` 与允许保持不变的 exogenous state；
- operative-token equivalence verifier；
- action/meta-action、observation、response、transition 和 cost fingerprint；
- 可干预 operator IDs、派生效应清除图与 reset semantics；
- physical oracle、measurable-policy oracle、actual policy 和 robust-tree checker 的分权；
- method 不可见的 target truth、Authority keys 和 evidence anchor；
- removal/reverse/block 的预注册规则，以及 minimal sufficient set 的枚举边界。

`formation witness` 可以在运行后生成；决定它是否成立的 evaluator 和 intervention semantics
不能在看到该 witness 后生成。

## 六、强中心与成熟 full-stack baseline 的公平性

Pro 已明确说“合法强中心”不能假装与多独立 Authority 的系统拥有同一权限。这一点正确，但其
实验仍只给出一个 strong-center upper bound，缺少同世界的中心编排基线。必须拆成两条：

1. `B-CENTER-EQUAL-ENVELOPE`：与所有 arm 使用完全相同的 observation API、独立 holder、
   response family、Authority endpoint、human service、预算、horizon 和 verifier；中心只
   负责计算和编排，不能代替主体决定。
2. `B-CENTER-LEGAL-CONTROL`：在另一个确实合法集中 Authority/状态的世界中运行，作为
   “该任务在集中控制前提下可被成熟方案解决”的构造反例；它改变了环境，不能用于宣称同
   Authority 拓扑下算法优越。

成熟 full-stack 也必须作为一条实际实现的 arm，而不是把 planner、IAM、workflow、registry、
采购和人类审批的组件能力相加。所有 arm 应得到相同冻结 envelope；额外 connector、人工自由
度、当前政策访问或 private fact 都要显式计入能力与成本。human baseline 既不能被压进机器的
预制菜单，也不能拥有无限时间、无限询问和免费隐性知识。

在这些条件下，强中心、成熟组合、人工流程或 platform-direct 完整通过，应登记为正向解决；
candidate 独有成功为零或只增加成本时，应停止新增 formation-specific mechanism。

## 七、与 G3/X1 v1 的精确关系

| 项目 | Pro 返回 | 本地合同/设计 | 审计 |
|---|---|---|---|
| closure | 主要检查 `A_T*` 的直接执行路径是否为空 | `C` 检查冻结 full policy | `CONFLICT`：需显式双报，不能互换 |
| operative condition | 新条件使直接路径首次合格 | `N=EXTANT_ACTIVATED/NEW_TOKEN` | `ALIGNABLE`：Pro 的主要正贡献应落在 `N` |
| model/institution change | 叙述中出现但未独立输出 | `E=SAME/CHANGED/UNKNOWN` | `INCOMPLETE` |
| task invariance | 固定 Q/V0/Principal/Authority；变化为 E′ | `T` + exact `task_diff` + owner/controller receipts | `PARTIAL ALIGNMENT`：语义方向对，缺机器绑定 |
| trace validity | Authority、cost、Effect、Acceptance 门槛 | `V` + receipt body/hash | `PARTIAL ALIGNMENT`：仍是候选叙述 |
| actual policy | failure mode，不是独立量词 | `R_measurable_exists` 与 `R_actual` 分开 | `CONFLICT` |
| bounded unreachable | `CERTIFIED_EMPTY`，完整性未机器化 | complete frozen inventory + `C=UNSAT` | `CONFLICT` |
| owner-authorized fork | 独立合法 E′，不是原任务成功 | `AUTHORIZED_NEW_EPISODE` | `VERIFIED ALIGNMENT` |
| safe exit | UNKNOWN/REFUSED 被提及 | `R_safe_robust/R_terminal_robust`、SAFE_EXIT | `INCOMPLETE` |
| causal receipt | 建议 witness/removal | embedded hash-bound counterfactual body | `INCOMPLETE`；存在 post-treatment oracle |

Pro 返回可以作为 G3 候选解释和实验素材，不能原样成为 X1 v1 receipt，也不能覆盖本地
`C/N/E/T/V + R` 坐标。

## 八、最小修订门

1. 撤销“G3 真正只研究当前执行路径从空到非空”的排他表述；保留完整母线的诊断、执行、
   正确停止和可行动不可达解释。
2. 所有 episode 同时输出 `C/N/E/T/V` 和六个 `R` 坐标；`Π_exec(S0)=∅` 只能支持直接执行
   不可用，不能写成 `C=UNSAT`。
3. 把 capability、Authority、tool、partner、representation、exit、observation、response、
   transition 和 human/program creativity inventory 冻结为可执行对象；开放项显式
   `INCOMPLETE/UNKNOWN`。
4. 把 stale/wrong-source model invalidity、actual-policy miss、bounded unreachable 和
   open-inventory Unknown 拆成不同输出；采用 X1 v1 的硬门。
5. 对 owner-authorized fork 保存 original/result task hash、逐字段 diff 和 owner receipt；
   controller substitution 另存 controller claim，二者都不能记为原 Episode 成功。
6. 预冻结 causal evaluator、token equivalence、reset/derived-effect semantics 与干预集合边界；
   actual arm 不得看到 hidden truth 或 realized response。
7. 拆分 equal-envelope center 与 legal-control center；成熟 full-stack 和人类 baseline 必须
   实际运行并支付相同能力、权限、披露、等待和治理成本。
8. 将 Refuse/Defer/Unknown、safe robust、terminal robust、over-abstention 和无效循环设为
   一等结果，不能把合法拒绝写成 solver failure。
9. 在补齐逐主张官方文档/原始论文映射前，所有外部技术事实保持 `UNRESOLVED_SOURCE`。

## 九、下一实验改变

不要先扩成 Pro 建议的三域 216 episode。先运行一个 6-world、同皮肤、同冻结 envelope 的
量词鉴别器；若这一小组不能稳定区分，扩大领域只会复制标签错误。

| world | 冻结真值 | 必须输出 |
|---|---|---|
| `W1-PREFIX-SAT-NEW-TOKEN` | `sign/request` 已在旧 model；token 在 S0 不存在；holder actual branch 批准 | `C=SAT, N=NEW_TOKEN, E=SAME, T=INVARIANT` |
| `W2-CLOSED-EXTENSION` | old complete model 内无 policy；精确、获授权 L2 diff 后旧 Q 可达 | old `C=UNSAT`，after `E=CHANGED, N=NEW_TOKEN`；不得改题 |
| `W3-ACTUAL-MISS` | 与 W1 同一 measurable policy；actual arm 使用 stale branch 或选错动作 | `ACTUAL_POLICY_MISS`，不得报 bounded unreachable |
| `W4-OPEN-INVENT` | tool/partner/representation 至少一项未封闭 | `UNKNOWN/UNRESOLVED_MODEL`，即使有限搜索耗尽 |
| `W5-OWNER-FORK` | owner 正式改变 material Q/V0 | `AUTHORIZED_NEW_EPISODE`，不是原 G3 成功 |
| `W6-VALID-REFUSAL` | holder 合法拒绝，Effect 不保证但可安全终止 | `R_effect_robust=FALSE, R_safe_robust=TRUE, R_terminal_robust=TRUE` |

每个 world 只使用运行前冻结的：

```text
S0 / Q / V0 / necessary Principals / Authority endpoints
action+meta-action / observation kernel / response family
transition semantics / cost+privacy budget / horizon / task diff
```

同时运行：

- equal-envelope deterministic workflow；
- contingent planner；
- equal-envelope strong center；
- 实际成熟 full-stack composition；
- bounded human baseline；
- formation candidate。

runner 分开执行 physical oracle、measurable-policy oracle、blind actual policy 和 robust-tree
check；成功后才按预注册规则运行 knowledge-only、remove/reverse/block、Authority
substitution、task diff 和 after-the-fact response shrink。每个结果必须生成 X1 v1
`g3_receipt` body，不允许 evaluator 从 arm 名称或最终成功反推标签。

这个实验会直接改变下一步判断：

- 若 mature composition/center/human 在 W1–W6 全部通过，G3 的当前 bounded 问题由现有
  组合解决，停止 formation-specific planner 创新；
- 若所有 actual arms 只在 W3 失败，问题是 policy/implementation，不是不可达；
- 若 W2 在 complete-frozen old model 中稳定 `UNSAT→SAT`，才支持有界 model/institution
  extension；
- 若 evaluator 无法在不读取结果的情况下区分 W1 与 W2，应先修 evaluator，不进入三域或
  live track。

在该修订门和 6-world 量词鉴别器通过前，不建议把 Pro 的 `NEWLY_QUALIFIED`、
`CERTIFIED_EMPTY`、formation witness、成熟组合覆盖或三域 benchmark 写入正式机制状态。
