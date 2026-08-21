# Wave 008 — G3 causal reconstruction and rebase

日期：2026-07-29  
状态：`COMPLETE_LOCAL_SYNTHETIC / PRO SEALED / QHM-1 ATTACK RECHECKED`

## 本轮实际改变了什么

G3 原问题不能继续只按“发现 / 激活 / 条件创造 / 改题 / 冒权”五个互斥标签推进。
这套分类混合了三个不同问题：

1. 合格路径或条件性策略是否已经存在；
2. controller 是否知道、找到并可靠执行它；
3. 最后报告的成功是否仍满足原任务、Authority 与 target-side truth。

本轮最重要的新判别是 **prefix closure**：

> 若披露、probe、请求授权、承诺、修复、构建已知 adapter 或 human escalation，
> 在 `S0` 时已经是合法可用、受 Authority 约束且计入原预算的动作，那么这些准备动作
> 与后续执行组合起来，本来就是一条从 `S0` 出发的条件性 policy。它们可以创造新的
> 物理对象、授权或承诺，却不自动证明旧 action closure 中不存在合格 policy。

这不否定“一个新条件确实被做出来了”，而是迫使研究分别回答：

- 现实对象是否新产生；
- 该对象是否能由旧模型内的合法准备动作产生；
- 是否必须扩展 action/interface/policy/authority model；
- 是哪一种方法最可靠、低成本地完成；
- PFE/A2A/联邦拓扑是否另有必要性或优势。

## 三路独立结果

### 1. ChatGPT Pro 首轮

冻结任务：
`external/pro-g3-001/TASK.md`

完整可核对返回：
`external/pro-g3-001/RESPONSE.md`

运行凭据：
`external/pro-g3-001/run.json`

首轮没有看到本地独立重建或模拟器实现。它提出：

- 研究对象应是 observation-contingent qualified policy，不只是固定 action sequence；
- 可达性至少要区分 existential、actual-policy 与 robust 三种量词；
- 用 `L0 execution / L1 old-model preparation / L2 model or institutional extension /
  L3 task mutation` 表示 formation depth；
- 只有在有限冻结模型内证明 `L0+L1` bounded-UNSAT、精确 `L2` diff 后旧任务变 SAT、
  Authority 有效、target/cost/acceptance 独立验证、干预消融成立，才支持
  bounded model-level formation；
- 即使 formation event 成立，也不推出需要新方法；中心 planner + distributed
  authority、成熟 workflow、human process、adapter/policy engineering 或组合完整解决，
  都是正向答案；
- 下一试验应包含 discover、enable、commit、known-build、extend、drift、substitute、
  UNSAT 八类 paired worlds，并对每个成功自动运行 knowledge-only、old-model prefix、
  model-diff、old-task、Authority substitution、repeated-effect/cost 与 intervention-subset
  replay。

注意：返回中出现的网页来源标签没有在本地逐项核验。本轮只把它当外部模型的独立理论与
实验建议，不把其文献性陈述登记为已核实来源。

### 2. 本地独立问题重建

本地研究者没有看到 Pro prompt 或返回。它独立得出：

- discovery、activation、formation 是世界状态变化分类；
- controller substitution 是拓扑与归因问题，不应与前三者混成同一维度；
- 强中心成功不必否定 formation event，但会反驳或缩窄 PFE/A2A/互动拓扑的必要性；
- 当前 G3 strict formation 仍为 `Unknown`；
- 必须冻结 `S0 / Q / V0 / principal / Authority / witness / budget`，并运行
  static、activation、operator、matched strong-center 与 wrong-authority、
  producer-only、remove/reverse。

这一路与 Pro 在“formation event、解决方法、拓扑增量必须拆开”上收敛；差异是它仍把
“有权 operator 首次让路径成立”视作 formation 的充分候选，而 Pro 进一步要求检查该
operator 是否本来就在旧 preparatory closure 中。

### 3. root 对本地实现的攻击

原实现首次报告 `13/13`，但 root 发现：

1. `remove_operator` 没有先 apply，就对不存在的 operator 记
   `FORMATION_OPERATOR_REMOVED`，形成伪消融；
2. Authority locus 被写成 joint-change-controller，使中心有机会把自己当 Authority；
3. wrong-authority 与 producer-only 失败被错误解释为 `operator_necessary=true`；
4. 更承重的语义错误是：`APPLY_FORMATION_OPERATOR` 从 `S0` 就在 public action
   alphabet 中，但实现没有计算 old-model closure 或 UNSAT，因而 `F=FORMATION`
   只是 evaluator 预填标签；
5. strong-center 只是 `FormationPolicy` 的空子类，能证明同一中心控制结构可运行同一
   合成策略，但不能证明任何成熟 planner/workflow/HITL stack 已被实测覆盖。

已完成的局部修复：

- remove 现在必须经历 `apply → target reachable → remove → target unreachable`；
- remove absent operator 只返回 no-op 与 `Unknown`；
- Authority 改为独立 `principal:joint-authority-holder`，并列入 necessary principals；
- wrong-authority 与 producer-only 不再冒充 operator necessity；
- 14 项代码回归通过。

但这些绿灯只表明局部机制错误已被封住，不恢复旧实验的 G3 判别力。旧目录已标为
`RETAINED NEGATIVE PROBE / NOT A G3 DISCRIMINATOR`。

独立 mutation audit 在测试通过后又复现：

- `Q/V0/necessary principals` 只是存储字段，没有进入 executable evaluator；
- target witness 由同一 `TruthSession` 生成并自验，不是 target-authoritative readback；
- Candidate 回填公开 holder 字符串即可通过 Authority，相当于 controller 自称 Holder；
- 同 flags、同 trace、同 fingerprint 只改 `WorldKind` 曾得到三种分类，证明分类由标签驱动；
- remove 后重新 apply 可再次成功，说明只测到 current effect dependency，不是 bounded
  operator necessity；
- strong-center 与 FormationPolicy 是同一函数对象；
- fingerprint 不绑定 hidden state、action model、evaluator、holder policy 或 cost semantics；
- no-route world 曾被重复 apply 拖成 budget failure，Unknown、invalid trace、causal evidence 与
  task outcome 混在一个 `status` 中；
- 每个 action 一律成本 1，不构成真实资源公平。

root 已撤销旧输出中的 `existing_solution_value=POSITIVE` 与 operator necessity，并把
same-policy center 改成构造性拓扑结果；这仍只是止损，不是把旧 fixture 修成 QHM-1。

## QHM-1：现有组合完整覆盖也是正向结果

新实验入口：
`experiments/wave-008-g3-qhm1/README.md`

当前冻结结果：

- 10 个 hidden worlds × 3 个能力对齐 policy，共 30 个运行；
- 18 个 `QUALIFIED_SUCCESS`：discover、enable、commit、known adapter、L2 extend 和
  multi-blocker combo 各被三个 policy 完成；
- 9 个 `BOUNDED_UNREACHABLE`：task drift、controller substitution/refusal 与有限
  complete-model UNSAT；
- 3 个 `UNRESOLVED_MODEL`：open action inventory 明确不完备，禁止伪造 UNSAT；
- strong center、mature workflow composition 与 formation candidate 都精确覆盖 bounded
  oracle 的 6 个 SAT world，candidate 独有成功为 0；
- 三个 policy 在 combo world 产生三种可观察的合法 preparation 顺序，不再只是同一函数
  改名；但仍来自同一代码库与同一 authoring stream，独立实现证据为 `NOT_ESTABLISHED`。

这是我们要求的正向结果：

> 在当前冻结有限分母上，不需要新的 formation-specific 方法；中心、成熟 workflow、
> holder、adapter、授权与 verifier 的组合已经解决所有声明为可解的 bounded case。

它属于通爻解决方案，而不是“增量为零”。它只关闭在这个分母上重复发明同能力的理由，
不证明真实成熟产品、真人制度或生产系统已经覆盖 V1/V2。

QHM-1 同时给出四个理论区分：

1. `TOKEN-COMMIT`：旧 full-policy closure 为 SAT 时，episode 内仍可首次形成
   Authority-bound token，因此 `C=SAT, N=NEW_TOKEN, E=SAME` 可以同时成立；
2. `META-REFACTOR`：同一物质过程写成 `register_new_operator` 或 `install(spec)`，
   layer depth 从 2 变 1，但物质向量和终态不变，证明 depth 不是 ontology；
3. `KNOWLEDGE-PROVENANCE`：knowledge-only replay 只能消费 parent-owned、task/义务/
   privacy/cost/response-hash 绑定的 observation；未绑定返回和免费注入必须失败；
4. `OPEN-INVENT`：有限边穷举不等于开放 action language 完备；该 world 只能保持 Unknown。

这里的 closure oracle 是逐 world 的 existential action sequence；runtime planner 是精确
INSPECT 后的 deterministic actual policy；robust principal-response policy synthesis 没有
测试。

### QHM-1 独立攻击迫使修复的错误

新实现一度再次出现了“测试绿、承重结论假”的问题：

- 三个系统共享同一个 `BaseSystem.run` 规划逻辑，只有标签不同；
- 改成不同源码后，九个单阻塞 world 上的 action trace 仍完全同构；
- 三个 planner 全部停止时，空 success set 相等仍让比较器与 Knowledge gate 返回 true；
- claimant bundle 携带自己的 registry，evaluator 相当于信任被验对象提供的验签根；
- 非 authorization receipt 的签名没有与冻结 expected payload 对照；
- INSPECT trace 只记录动作名，不绑定返回内容，knowledge replay 又把 hidden world 交给
  omniscient BFS，两个 provenance boolean 只是自证；
- 命令入口在单元测试通过后仍因旧字段名实际崩溃；
- 新增 world 后落盘 report 一度仍保留旧分母。

当前修复包括：

- 三个 policy 分别实现 backward chain、固定 workflow 与 intervention set，并用 combo
  world 产生不同 trace；
- comparator 要求非空且逐系统精确等于 bounded SAT/UNSAT oracle；
- trusted registry 由 parent runner 持有，所有 action 的 exact payload/task/holder/
  signature 与 receipt uniqueness 必须通过；
- `InspectionRecord` 绑定实际 facts、response hash、task、trial、义务和 ledger index，
  planner 实际 observation hash 也必须一致；
- knowledge-only 改为 observation-aware L0 policy，不再让搜索器用 hidden world 规划；
- 增加 all-stop、wrong-payload receipt、unbound inspection response、
  free-information 与 obligation-loss mutation；
- 命令入口和四份输出都进入最终回归。

第一次冻结复测继续发现：holder 的 policy/effect 仍由 dispatch 调用者传入，正确 payload
的 no-op receipt、receipt-id rename 与断裂 project receipt 仍能过验；三份 inspection
记录可同步改写；UNSAT certificate 只绑定 action spec，不绑定 transition semantics。
第二次修复把 policy/effect capability 固定进 holder，receipt 绑定 effect log 与前后状态，
parent 在 bundle 外持有 canonical evidence anchor，并新增 executable-model fingerprint。
`H` action 也开始实际消费 human quota；META-REFACTOR 的物质向量改由终态计算，不再写常量。

15 项本地回归与报告生成已经通过；独立攻击者按第二个冻结源码与 report hash 完成只读
复测，确认上一轮 1 个 P0 与 2 个 P1 在指定范围内关闭，源码、实时报告与四份落盘输出一致。
这使 QHM-1 成为 `LOCAL_FINITE_SYNTHETIC_TRUSTED_PARENT / INDEPENDENT ATTACK RECHECKED`；
实现仍来自同一研究流，不冒充独立实现、真实主体或生产证据。

## 对 prefix closure 的反攻击：SAT 与 condition formation 可以同时为真

Pro 的 prefix lemma 严格证明的是：

> 当准备动作被纳入同一 transition system，`preparation ; execution` 使 full-policy
> closure 在 `S0` 为 SAT。

它不证明准备动作产出的 Authority-bound grant、commitment、adapter、共同规则或其他
operative token 已经存在。一个旧模型完全可能已经有 `propose / sign / build / register`
生成动作，但必要 token 在 `S0` 为 absent，执行生成动作后才首次启用 downstream action。
此时以下两项可以同时成立：

- full-policy prefix closure：`SAT`；
- operative condition：确实在 episode 中由 absent 变 present。

因此不能用一个单值 `formation=true/false` 抹平现实差异。当前更稳健的事件描述至少是：

| 维度 | 值域 | 回答的问题 |
|---|---|---|
| `C` closure | `SAT / UNSAT / UNKNOWN` | 在冻结 action/meta-action、预算和主体策略下，是否已有 qualified contingent policy |
| `N` operative enabling delta | `NONE / EXTANT_ACTIVATED / NEW_TOKEN / UNKNOWN` | 必要的现实 token/condition 是既存、激活还是新产生 |
| `E` kernel/policy delta | `SAME / CHANGED / UNKNOWN` | action schema、institution、Authority 或 principal policy 是否改变 |
| `T` task invariance | `SAME / CHANGED / UNKNOWN` | 原任务、价值底线、必要主体、预算与 evaluator 是否保持 |
| `V` trace validity | `VALID / INVALID / UNKNOWN` | Authority、identity、cost、target、acceptance 与完整 trace 是否成立 |

`L0/L1/L2` 仍可作为某个冻结实验的操作层级，但不能冒充表示不变的 ontology：
若 `register_new_operator` 从一开始就在高阶 transition system 中，它也可以被写成旧闭包
前缀。真正可比较的是冻结边界下的 `C/N/E/T/V`，以及边界变化会怎样改变结论。

`N=NEW_TOKEN` 不能靠对象名字判定。一个 candidate token/set `Z` 至少要同时满足：

1. Authority-owned `S0` 中没有通过冻结 equivalence verifier 的等价对象；
2. `Z` 在第一个 target Effect 之前产生；
3. `Z` 使至少一个原来不合格的 downstream action instance 变得 Authority-valid、
   interface-valid 或 acceptance-valid；
4. reset exact `S0`、保留合法信息与外生条件、删除 `Z` 及其派生效应并重新规划后，
   原 `Q` 不可达；多因场景报告 minimal sufficient set；
5. `Z` 的生成者、Authority、provenance、隐私、人类、构造与验证成本全部有效并入账；
6. `Z` 不是目标 Effect 本身，也不是不改变合法行动空间的日志或 producer self-report。

这给出两个不能互相覆盖的合法结果：

- `C=SAT, N=NEW_TOKEN, E=SAME`：旧 formation capability 内确实形成了新的 operative
  condition/token；
- `C=UNSAT, N=NEW_TOKEN, E=CHANGED`：冻结旧边界不可达，model/institution extension
  后形成 token 并使旧任务可达。

开放行动语言、真实人类创造或不可枚举 program semantics 下，`C` 默认可以是 `UNKNOWN`；
不能靠 “ask human / synthesize arbitrary code” 伪造 SAT，也不能靠有限枚举伪造 UNSAT。

## 当前最佳判断

| Claim | 当前状态 | 原因 |
|---|---|---|
| 现有 D/A/F fixture 能机械产生三类不同 trace | `SUPPORTED_LOCAL_SYNTHETIC` | 14 项回归通过，合同与 target readback 可复算 |
| `F` 已证明 strict/global formation | `NOT_SUPPORTED` | 没有 old action/preparation closure 与 bounded-UNSAT |
| 旧 discriminator 的 `F` 支持 bounded L2 extension | `NOT_SUPPORTED` | 旧 fixture 未计算 closure，保留为负面探针 |
| QHM-1 `extend` 支持 bounded L2 model extension | `SUPPORTED_LOCAL_FINITE_MODEL` | L0/L1 UNSAT、L2 SAT、exact diff replay 后 old task 合格；逐 world existential 量词 |
| strong center 在当前 fixture 可运行同一合成策略 | `SUPPORTED_LOCAL_CONSTRUCTION` | 同信息、同预算、独立 holder 下成功 |
| 合成 center/workflow/holder/adapter 组合覆盖 QHM-1 bounded SAT worlds | `SUPPORTED_LOCAL_SYNTHETIC` | 6/6 SAT worlds，3/3 UNSAT worlds，open-invent 保持 Unknown |
| 真实成熟产品、真人制度或生产组合已完整解决 G3 | `UNKNOWN` | QHM-1 不是现实产品或独立实现测试 |
| 现有组合若完整解决是否属于成功 | `YES / METHODOLOGICAL` | 直接解决原问题，不需要独立 novelty |
| PFE/A2A/联邦有独立必要性或优势 | `NOT_ESTABLISHED` | formation event 与拓扑增量是不同 claim |
| 需要创造新的 formation-specific method | `NOT_ESTABLISHED` | candidate 在 QHM-1 独有成功为 0；更开放/现实分母仍待研究 |

## 为什么“技术都在那里”，问题仍没有被解决

当前答案不是“因为缺一项黑技术”，而是以下结构同时存在：

1. **各组件解决的是不同的有界子问题。** Planner 找 policy，IAM 判断某个授权，
   workflow 执行已表达流程，adapter 转换已知接口，审计记录已发生行为，搜索/RAG/ARD
   找已经表达并可索引的对象。它们没有自动拥有完整 `Q`、所有 Principal 的本地条件、
   Authority、target truth 与全生命周期成本。
2. **完整任务常常从未被共同冻结。** 各系统分别优化局部成功；任务、价值底线、必要主体、
   action language、预算和验收在组合过程中漂移，最后“每个组件都工作”却没有人能证明
   原问题被解决。
3. **决定性输入并未显式存在。** 未声明的 intent、能力、关系、拒绝条件、隐私边界和
   principal response policy 不能靠索引召回；创造合作可能性又要求披露足够上下文，
   与隐私、拒绝和责任形成真实张力。
4. **世界和 action language 持续变化。** 静态目录或模型可能知道已有对象，却不知道
   新工具、权限、伙伴、制度和主体决定怎样进入可用空间，也不知道旧信息何时失效。
5. **Authority 不能被计算中心吞掉。** 中心可以规划，但签署、承诺、接受和责任仍须由
   对应主体完成。很多“中心已解决”演示实际上偷偷获得了更多信息、权限或替主体决定。
6. **组合本身引入语义和证据断裂。** 格式转换、identity、freshness、成本、重复 effect、
   target readback、恢复和长期维护没有单一 truth owner；组件覆盖率不能相加成端到端保证。
7. **开放创造与可计算闭包存在边界。** 若 action set 窄，会把普通工程误叫 formation；
   若允许“写任意程序 / 让人类想办法”，所有创造又会被文字上吞进 `S0` 既有可能性。
   因此 formation 只能相对于可执行、受权、计费、有限的 action/meta-action boundary 判断。

这解释了为什么成熟技术可能已经覆盖很大部分，却仍没有直接解决我们提出的完整问题；
也解释了为什么把它们正确串联、补齐 truth/Authority/closure/verification 边界，本身就是
通爻方案，而不是“没有原创”。

## 下一实验的不可妥协条件

QHM-1 或等价 causal replayer 必须：

1. 冻结 executable old task，而不只冻结文字与 hash；
2. 冻结 `L0/L1/L2/L3` action 与 meta-action boundary；
3. 冻结 actual scripted principal policies，并另报 existential / actual-policy / robust；
4. 由 runner 穷举或 model-check `L0`、`L0+L1`、`L0+L1+L2` closure，输出 SAT witness
   或有界 UNSAT certificate；
5. 让中心、workflow、human/adapter composition 与 candidate 拥有同一观察、Authority
   endpoint、L2 proposal、预算和 verifier；
6. controller 只能 request，真实 holder 执行 privileged action；
7. `Q` 检查完整 trace、exact-once、Authority、target、acceptance 与 authoritative cost；
8. 成功后自动运行 knowledge-only、fixed-model-prefix、model-diff、old-task、
   intervention subset、Authority substitution 和 endpoint/cost tampering replay；
9. 包含硬的 no-special-mechanism、valid refusal 与 true-UNSAT worlds；
10. 将“事件分类”“解决率/成本”“拓扑/新方法增量”分表输出。

此外必须加入专门攻击表示边界的 paired cases：

- `TOKEN-COMMIT`：sign 类型已存在、commitment token 不存在，预期允许
  `C=SAT / N=NEW_TOKEN / E=SAME`；
- `META-REFACTOR-A/B`：同一现实过程分别编码为 `register_new_operator` 与通用
  `install(spec)`，`N/E/T/V` 物质结论必须一致，depth 可以变化但不得支配结论；
- `PRIVACY-BOOTSTRAP`：只有 purpose-limited commitment 后才可披露，knowledge replay
  若丢失 provenance、privacy cost 或义务必须失败；
- `OPEN-INVENT`：允许提交新程序并由独立 verifier 判断，但 closure 不完备时只能
  `UNRESOLVED_MODEL`；
- `PRINCIPAL-POLICY`：固定 threshold 与互动后 policy-version change 配对，后者只支持
  synthetic principal-policy transition，不外推真人偏好形成。

## 并行工作已回收

- prefix-closure 审查已完成：strict prefix closure 与新的 Authority-bound operative token
  可以同时成立；layer depth 只在表示内有效；
- 旧 simulator mutation audit 已完成并保留其失败边界；
- QHM-1 causal replayer 已完成 10 worlds / 30 runs / 15 tests，并经不同 Agent 对冻结快照
  复核通过；三个 planner 仍只是同代码流 scheduling variants，不构成独立实现证据。

本轮未把 Pro、root 重构或 QHM-1 自动晋升为正式 Problem v2 或 MechanismProfile 变化。
下一轮已经以七线形式启动，见
[WAVE-009-FIRST-RETURN.md](./WAVE-009-FIRST-RETURN.md)。
