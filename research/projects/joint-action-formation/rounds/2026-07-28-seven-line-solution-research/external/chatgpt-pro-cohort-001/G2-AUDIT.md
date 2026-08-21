# ChatGPT Pro G2 独立敌对审计

日期：2026-07-29  
状态：`INDEPENDENT AUDIT / REVISE BEFORE EXPERIMENT / NO FORMAL STATUS CHANGE`

## 审计对象、证据边界与总判断

本审计检查：

- [`G2-return.md`](./G2-return.md)；
- [`G2-final.md`](../codex-cli-cohort-001/G2-final.md)；
- [`WAVE-009-G2-G5-DESIGN.md`](../../WAVE-009-G2-G5-DESIGN.md)；
- [`Wave 009 G2/G5 crossed square`](../../experiments/wave-009-g2-g5-crossed-square/README.md)
  的设计、实现、失败历史、冻结结果与测试；
- Problem v1/v2、G2 原生能力线、T2/T3/T4/T5 校正及当前 `research/NOW.md`。

没有联网核验 Pro 返回中的外部来源。`G2-return.md` 只保存了可见正文和“OMG”“W3C”
“NCSU CSC”等来源徽标文本，没有保存逐主张 URL、引用位置、原始返回字节或独立
`G2-sources.md`。因此，本审计不把 A2A、ARD、FIPA、WS-Agreement、CMMN/BPMN、BSPL、
VC/OAuth、采购制度或 2026 Agent benchmark 的外部技术叙述登记为已核实事实；它们统一为
`UNRESOLVED_SOURCE`，不是判定为错误。

本地 crossed-square 的 28 项测试在本次审计中重新运行，结果为 `28/28 PASS`。这个结果只
确认当前实现符合已写入的本地合成合同，不扩大其证据范围。

总判断：`REVISE_BEFORE_EXPERIMENT`。

Pro 返回有四项值得保留的贡献：

1. 明确区分 candidate、constitution、activation 与后续失效；
2. 不把强中心、成熟平台、人类制度或零新增协议当作负结果；
3. 用逐条款构成规则攻击“全体点同意”的粗糙布尔状态；
4. 提出脚本化 Principal 不能作为主体真实认领的最终证据。

但当前不能把它直接冻结为 G2 的完整理论或下一 evaluator，原因是：

1. “逐条款构成规则”是有用候选表示，不是 G2 原生异质内核的无损替代。它没有证明能保留
   可变化的关系语法、多作者局部认领、隐藏 column 和关系级不可分解约束。
2. 本地 `24/24` 明确偷用了 owner oracle：一个 parent-side broker 持有所有 Principal
   私钥，并替他们生成 ACK、explain-back 和接受 stance。它验证的是 receipt/gate
   conformance，不是理解、认领或构成。
3. “成熟组合已经完整解决 G2”目前只有条件化架构说明和同一 authoring stream 的合成正例，
   没有一个实际成熟产品组合在合格 T2/T4、真实 Principal、迁移和失败恢复上端到端运行。
4. Pro 的 2×2 把多个构成门捆成一个 treatment，并把“中央/分布式”当作独立因子；但后者在
   共同制度下只是状态实现选择，在无共同制度下又会同时改变环境与 Authority 拓扑，不能
   单独识别因果。
5. 把 formation recall 先编译到有限决策空间可以形成封闭 benchmark，但若作为 G2 的一般
   定义，会静默删除“关系语法、角色、动作、证据和评价方式本身需要形成”的开放切片。

## 一、逐项判定

| Pro 或本地返回中的主张 | 判定 | 审计结论 |
|---|---|---|
| G2 不是文本相似或消息传输，而是多主体关系如何获得规范状态 | `PLAUSIBLE` | 与 V1/V2、原生 G2 的候选/承诺分离和 Authority 不可静默穿透一致；但 G2 还包含关系语言、局部贡献与 private column 的形成，不能只剩状态构成 |
| `CANDIDATE ≠ FORMED ≠ ACTIVE` | `VERIFIED` | 与 V1 的非蕴含、G2/G5 分离及本地 crossed square 一致 |
| 不同条款可有不同构成规则 \(\kappa_t\)，并不都要求全体共同签字 | `PLAUSIBLE` | 是比全局 consent 布尔值更强的表示；尚未证明所有 G2 关系都能无损分解为预先枚举的条款 |
| Pro 给出的最小关系语义足以代表 G2 | `OVERSTRONG` | 缺少 schema 形成、关系级耦合约束、局部不可披露 column、异议冲突及多作者认领的原生运行语义 |
| 理解门应是所有 `FORMED` 关系的统一硬门 | `OVERSTRONG` | 理解、法律/制度构成、主体认领和伦理可接受性不总是同一个事实；哪些理解证据是 constitutive 应由任务/条款规则决定，并独立报告 |
| Authority 可以有来源明确的代表、委托、额度、期限与撤回，不能从身份或意图自动生成 | `VERIFIED` | 与 V2 的 Principal/Agent Entity/Authority 边界一致 |
| 有共同制度和可信强中心时，成熟组合无需新协议即可完整解决有界任务 | `PLAUSIBLE` | 作为有界机制候选成立；“成熟组合已经端到端解决”尚未被实际产品或独立实现验证 |
| 真正未解决的只剩无共同中心、无统一制度的开放跨域环境 | `OVERSTRONG` | 即使有共同中心，未表达 schema、private action set、受影响方 Standing、真实理解和制度外 Effect 仍可能缺失 |
| Formation recall 必须先有限化才可定义 | `PLAUSIBLE_FOR_CLOSED_BENCHMARK / OVERSTRONG_FOR_G2` | 有限 Pareto frontier 可测封闭 slice；不能由此把 open-schema formation 排除在分母之外 |
| C3 与 D4 的比较能回答是否需要分布式机制 | `UNRESOLVED` | 若共享同一制度，D4 主要是复制/同步实现；若不共享制度，C3/D4 同时改变环境和 Authority 拓扑，不能归因于“分布式” |
| 本地 B0/B5 `24/24` 证明成熟组件能完整解决当前 G2/G5 | `VERIFIED_ONLY_AS_LOCAL_CONFORMANCE` | 只对显式结构化、truth-broker 预制、同 authoring stream、单进程合成 world 成立；不能支持主体理解、真实认领或成熟产品完整性 |
| `R(Wave009 structured synthetic)=0 observed`，完整 T2/T3/T4 residual 为 Unknown | `VERIFIED` | `G2-final.md` 的这条边界准确，比 Pro 的“已经完整解决”措辞更符合当前证据 |
| Pro 的三个“真实任务族”可直接成为下一评分分母 | `UNRESOLVED` | 它们目前是任务族提案，不是已保存、可回溯的真实 episode；不能与仓库 T2/T3/T4 同名替换 |
| 强中心、成熟组合、人类制度或固定平台完整解决就是正向结果 | `VERIFIED_AS_RESEARCH_RULE` | 与 V2、PROGRAM 和当前 solution-first 决定一致；不要求通爻独特或新协议有增量 |

## 二、逐条款构成没有无损保留 G2 原生内核

Pro 的 clause + \(\kappa_t\) 形式值得保留为一种 relation representation，但不能被提升为
G2 的唯一内核。与
[`原生研究线 02`](../../../../../a2a-reconstruction/04_audit/native_lines/02_problem_and_relation_constitution.md)
逐项比较：

| 原生能力 | Pro 返回 | Wave 009 本地实现 | 判定 |
|---|---|---|---|
| `CAP-REL-001` 关系语法可变化 | 承认 role、term、dependency 可不同，但默认先得到有限决策变量和条款类型 | `semantic_payload` 预先固定为 roles/purpose/scope/data_boundary，`material_change` 由 world author 直接标注 | `PARTIAL / OVERSTRONG IF CALLED SOLVED` |
| `CAP-REL-002` 精确版本 Stance | 明确 exact version hash、旧签名失效、material change 新版本 | 本地事件和 evaluator 确实绑定 `REL-V2` 并拒绝 stale stance | `VERIFIED_IN_SYNTHETIC_SCOPE` |
| `CAP-REL-003` 多作者 JAA、局部认领与异议 | Pro 要求 Local View、来源、scope、owner act 和 opposition | 一个 broker 持有全部 Principal key；`opposition_preserved=true` 由 fixture 常量写入，没有独立局部贡献/异议过程 | `PARTIAL / OWNER-ORACLE` |
| `CAP-REL-004` 隐藏贡献的 local column | Pro 后段提到 local oracle、DCOP/column generation | 不在 24-world 核心、关系语义或 2×2 treatment 中；没有 absent/withheld/undiscoverable/invalid column 的可区分真值 | `UNRESOLVED / NOT TESTED` |
| `CAP-REL-005` candidate 与 commitment 分离 | Pro 反复区分 proposal、stance、commitment、activation | 本地非蕴含和 crossed square 能拒绝 ACK、proposal、commitment、reservation 的互相穿透 | `VERIFIED_IN_SYNTHETIC_SCOPE` |

### 最强反例

三方形成一项数据合作。初始 schema 只有 `data-access` 和 `price`。数据方随后发现问题不只是
“训练允许/禁止”参数，而是需要新增：

- 一个模型派生物 Owner；
- 一个删除证明动作；
- 一个训练后反事实评估；
- 一个只在本地可计算、不能向中心披露的 membership-risk column；
- 一条“任一受影响参与者代表可提出 challenge，但无签署权”的关系级规则。

旧 clause store 可以把这些压成若干新字段并让每项 \(\kappa_t\) 变绿，但它没有证明：

1. 新角色和动作是怎样从开放局部世界中形成的；
2. 隐藏 column 未披露时中心为何不能误判为不存在；
3. challenge 与其他条款的整体耦合怎样保持；
4. 哪些 Principal 只认领自己的局部范围；
5. 移除 schema-formation operator 后关系是否仍等价成立。

因此，逐条款构成规则最多是 `RelationVersion` 的一种候选表示，不是 CAP-REL-001/003/004
已经被吸收的证据。

### 最小修订门

任何“clause semantics 覆盖 G2”的主张必须同时通过：

1. **表示保真门**：同时支持 clause-level \(\kappa_t\) 与 relation-level/global constraints，
   不要求一切规范事实可独立分解；
2. **schema delta 门**：新增/删除 role、action、evidence、evaluation、exit、Standing
   必须作为 typed schema change，而不是 fixture 的 `material_change=true` 标签；
3. **多作者门**：每个 Principal 只从独立 key/domain 对自己的贡献、异议和 stance 作证；
4. **private-column 门**：区分 `ABSENT / EXISTS_BUT_WITHHELD / EXISTS_AND_DISCLOSED /
   IMPOSSIBLE_TO_DISCLOSE`，不得把无 column 当无解；
5. **移除失败门**：移除 schema formation、multi-author provenance 或 local column 后，
   原生正例必须出现可观察失败。

### 下一实验改变

在任何大样本前先加一个 8-world `NATIVE-KERNEL-PRESERVATION` 小矩阵：

```text
parameter update / new schema role
single-author summary / conflicting scoped multi-author contribution
column absent / column exists but is withheld
clause-separable / relation-level coupled constraint
```

每个 world 同时运行 clause store、开放 workspace、authority-aware strong center 和 local
oracle composition。评分器不得读取 `material_change` 或 `relation_valid` 标签，只能从
independent principal events、schema diff、合法 local-oracle response 和冻结 relation-level
谓词推导。

## 三、理解、认领、构成与激活存在明确 owner oracle

Pro 的文字设计知道“脚本化 Agent 不能作为主体真正认领的最终证据”，这项自我限制正确。
但本地 `24/24` 没有检验这个问题：

- [`RelationTruthBroker`](../../experiments/wave-009-g2-g5-crossed-square/relation_truth_broker.py)
  在一个对象内生成所有 Principal 私钥；
- 同一个 broker 为每个 Principal 生成 ACK；
- explain-back 只是把隐藏 `semantic_payload` 的 hash 写成 `understanding_hash`；
- 同一个 broker 再替每个 Principal 写
  `ACCEPT_CURRENT_RELATION_VERSION`；
- `source_provenance=PRINCIPAL_SIGNED_EVENT_STREAM` 和
  `opposition_preserved=true` 也由 broker 直接填入；
- baseline 所谓理解只检查 `understanding_hash == source_semantic_fingerprint`。

因此签名在这里证明“parent 生成的字节没有被改”，不证明不同主体产生了这些字节。opaque
world ID、分离 relation/authority broker、Ed25519、completed-run seal 和独立 evaluator
都不能消除这个 oracle；它们只防止方法进程直接读取另一份 private truth 或事后篡改记录。

### 最强反例

Principal A 的本地视图遗漏了“衍生物可训练”例外。Broker 仍可直接用完整
`semantic_payload` 计算正确 hash、以 `REL-A` key 签名 explain-back，再签
`ACCEPT_CURRENT_RELATION_VERSION`。B0/B5 会形成关系并得到 `24/24`，但 A 无法回答 Pro
自己提出的“我承担什么、依赖什么、谁能改变、关键条件消失后怎样”。

更强的是：一个完全没有看过文本的自动 signer 也能返回给定 digest。hash equality 是内容
绑定，不是理解证据。

### 最小修订门

必须拆开四个 truth owner：

1. `PrincipalActor_i`：只持有自己的 local view、refusal policy 和 key，能够不响应、拒绝、
   局部 counter 或保持 Unknown；
2. `ComprehensionEvaluator_i`：运行前冻结、从该 Principal 实际可见材料生成任务相关问题；
   不接受复制 digest 作为理解；
3. `InstitutionalConstitutionOracle`：只判断 \(\kappa_t\)、Authority、版本和动作是否使关系
   在该制度中成立，不替主体声明理解或接受；
4. `Activation/Effect Owner`：只判断权限、资源、target readback、Adoption 或 Acceptance，
   不从 `FORMED` 自动推出。

一个 actor、case compiler 或 parent 不得同时持有全部 Principal key、生成全部 stance，并
再判定 relation truth。主体理解可以是 constitutive、quality 或 safety gate，必须由当前
任务/条款明确，不能一律塞进 `FORMED`。

### 下一实验改变

把现有 `RelationTruthBroker.issue_public_evidence()` 替换为请求路由器：

- 每个 Principal 在独立进程收到不同 local view；
- controller 只能请求，不能持有 Principal key；
- explain-back 是结构化答案，不是预给 digest；
- 至少加入 `correct hash / wrong understanding`、`correct understanding / refuse`、
  `partial stance`、`silence`、`opposition retained` 五种对照；
- evaluator 从实际 owner events 推导 relation，不再读取 fixture 的 `relation_valid`。

自动化阶段只能登记 `SCRIPTED-OWNER-CONFORMANCE`。只有独立领域主体阶段才能登记
`OWNER-UNDERSTANDING-OBSERVED` 或 `OWNER-STANCE-OBSERVED`；它仍不自动证明现实长期有效。

## 四、强中心“完整解决”的前提给得还不够

Pro 已列出共享平台、可验证 Authority、有限 schema、精确版本、独立 owner 动作、执行门和
争议制度。这足以定义一个有价值的强中心候选，但不能直接推出“成熟技术组合已经完整解决”。

### 缺少的前提

至少还需冻结：

1. **作用域**：是“预编译、共同制度下的 relation constitution”，还是 V2 的开放关系形成
   全问题；
2. **schema 完整性**：未知角色、动作、证据、Standing、exit 和 evaluation 是否被允许形成；
3. **可观察性**：中心能通过什么合法接口获得 private fact、local column、refusal 和
   opposition；无法观察时是否保持 Unknown；
4. **主体独立性**：中心不能持 Principal key，也不能把 workflow completion 变成 stance；
5. **受影响者**：无签署权但有 Standing 的主体怎样被发现、challenge 和补救；
6. **真实闭环**：actual product/runtime 的版本、撤销、reservation、readback、迁移和故障
   恢复是否贯通，而不是组件能力相加；
7. **制度边界**：共享制度如何取得 Authority、外部 Effect 与争议裁决，不由软件自行假定；
8. **经济边界**：平台接入、规则编译、人工认知、等待、迁移、锁定和恢复成本是否仍优于
   人工或其他成熟基线。

### 最强反例

一个采购平台拥有完美 canonical store、IAM、审批和签署。但新任务需要一个平台 schema
中不存在的“数据衍生物受影响者代表”，其存在只在数据 Owner 的私有风险分析中可见。中心
既没有合法查询动作，也没有该角色/Standing 类型。

平台可以在所有已知 owner 上 100% 通过版本、签署和撤销门，却遗漏必要主体并形成无效关系。
问题不是中心不够聪明，也不是需要分布式副本；是 schema 和合法 observation path 不完整。

### 最小修订门

把结论改为：

> 在已共同承认的制度、预编译任务/schema、可验证 Authority、独立 Principal 事件、完整
> observation path、可执行构成规则与真实 target gate 下，强中心或成熟组合是可能完整解决
> G2 有界切片的首选候选；当前尚未有合格端到端运行。

只有 actual strong-center/full-stack arm 在 fresh T2/T4、owner anti-oracle、迁移、撤销、
故障恢复和成本对照上通过，才能把 `candidate-complete` 升为 `task-complete`。若通过，这是
通爻的正向方案；不需要制造 novel residual。

### 下一实验改变

强中心必须拆成两条，避免偷换环境：

- `CENTER-EQUAL-ENVELOPE`：与其他方法拥有相同 local-oracle、Authority endpoint、owner
  actor、披露、预算和 deadline，只负责计算与编排；
- `CENTER-LEGAL-CONTROL`：在确有共同制度和集中 Authority 的另一组 world 中运行，证明
  该条件下中心方案可以是完整正解。

成熟组合必须是一条实际可运行的 arm，不能把 CMMN、CLM、IAM、policy、commitment 和
ledger 的组件能力列表相加后登记为闭合。

## 五、2×2 不能按当前形式识别所声称的因果

Pro 的 2×2 有两个因子：

```text
构成门控：text/artifact
        vs Authority + exact version + owner acts + revocation + dependency

状态架构：central canonical store
        vs distributed signed replicas
```

方向有信息增益，但当前设计不能支持“这个状态是否必须以分布式协议存在”的强结论。

### 问题 1：构成 treatment 是一整个 bundle

第二个取值同时增加 Authority、版本、owner 行为、撤销和依赖传播。即使结果改善，也不知道
是哪一项起作用，或是否只是给 treatment arm 更多真实信息和动作。

### 问题 2：分布式变量在共享制度中只是实现选择

若 C3 与 D4 使用同一个 schema、\(\kappa_t\)、owner 界面、Authority 和可信事件，只改变
state placement，那么它检验的是复制、分叉、离线和恢复代价，不是 relation constitution
语义。PostgreSQL replication、签名日志或一个新协议都可能实现它。

### 问题 3：无共同制度时又改变了环境

若 D4 的优势只在各方不承认同一中心时出现，则“是否存在共同 Authority/trust root”与“状态
是否分布式”一起变化。central arm 在该 world 中可能根本不合法，结果不能归因于 storage
architecture。

### 最强反例

在所有主体信任同一采购平台的 world 中，中央 store 与三份签名副本都收到完全相同的 owner
events；没有 partition、equivocation 或中心失效。两者形成结果必然相同，D4 无增益只说明
treatment 没有被激活。

换到三个互不承认单一记录源的 world，若 D4 允许各方保留独立 Authority 而 C3 要求它们先
接受中心，则实验同时改了 trust topology。D4 获胜也不能证明“分布式副本”是原因。

### 最小修订门

分开三个变量：

1. `K` 构成语义：text-only / exact version / owner evidence / Authority / revoke-dependency；
2. `A` Authority topology：共同法定/组织 Authority、相互承认的多 Authority、未互认多
   Authority；
3. `S` state placement：central canonical、replicated canonical、plural local states。

`K` 采用顺序消融或 fractional factorial，不能整包比较。`S` 只在同一 `A` 内比较；
`A` 的变化报告为 mechanism-environment interaction，不冒充 storage 因果。

### 下一实验改变

采用两阶段而不是一个 2×2：

1. **共同制度阶段**：固定 `A=SHARED`，逐项加入 version、owner evidence、Authority、
   revoke/dependency；中央与 replicated state 只测可靠性/成本。
2. **多 Authority 压力阶段**：固定独立 owner actor 和构成语义，加入 partition、中心
   equivocation、revoke race、无共同 trust root；比较 trusted coordinator、mature
   federation、signed local states 和人工制度。

只有第二阶段在相同合法 Authority/observation envelope 下出现可重复差异，才能把增量归于
分布式状态机制。即使有增量，也只支持该失败环境的窄域同步/证据能力。

## 六、有限决策空间会静默删除开放 formation

Pro 正确指出：无限自然语言字符串没有可用 recall 分母；把语义等价关系合并也能防止十个
近义合同制造虚假 recall。问题在于“先把每个真实任务编译为有限决策变量”同时可能把 G2
最承重的未知项预先写进答案：

- 必要角色；
- 可采取动作；
- 可提出的证据；
- 可接受的责任和退出；
- 局部私有 candidate/column；
- 哪种评价规则才算合格。

这与 V1/V2 的开放形成切片直接冲突。有限化可以评估已冻结 relation language 内的搜索，
不能据此评价 relation language 本身能否形成。

### 最强反例

benchmark 只允许调整价格、日期和访问字段。实际可行路径要求把“导出数据”改成“代码进入
买方域执行”，新增 executor、数据位置、readback witness、no-training 和删除责任。

有限 oracle 会把该路径记为 schema 外，不进入 frontier；所有方法都可能得到 perfect recall，
而真正的 formation 被分母删除。若 case compiler 事后把这些变量补入，方法又只是在已给答案
的空间里搜索。

### 最小修订门

必须双报：

```text
CLOSED_FRONTIER_RECALL
  = 在运行前冻结的 schema/equivalence class 中找到的合格 frontier

OPEN_SCHEMA_YIELD
  = 方法提出、由独立 owner/oracle 资格化的 held-out role/action/evidence/evaluation
    schema delta 数量、精度、价值和成本
```

另报：

- `SCHEMA_OUT_OF_MODEL / UNKNOWN_OPEN_MASS`；
- `FALSE_SCHEMA_EXPANSION`；
- `PRIVATE_COLUMN_DISCLOSURE_BITS`；
- `VALID_REJECT / DEFER / PROTECTIVE_CONTRACTION`；
- gold population 的独立来源与 finalized receipt。

不能把 open-schema slice 的缺失记为 recall 成功，也不能让 method 输出反向扩大自己的分母。

### 下一实验改变

同一 task skin 设两层 oracle：

1. `L_closed`：有限参数 frontier；
2. `L_open-heldout`：运行前由独立 truth owner 冻结、但不向方法公开的 schema/operator
   类型。

方法先判断是否需要 schema reopen，再提出 typed delta；只有通过 task invariance、necessary
Principal、Authority、V0、relation-level constraint 和 removal test 后才进入
`OPEN_SCHEMA_YIELD`。这不会宣称对无限空间有完整 recall，但至少不把已知开放差异删掉。

## 七、与 V2 及 T2/T3/T4/T5 的一致性

### V2

`VERIFIED`：

- Pro 保留 Principal、Authority、refusal、版本、撤销和强中心正基线；
- 区分 candidate、formed、active，未让协议或联邦成为预设答案；
- 承认脚本化 Agent 不是真人认领的最终证据。

`CONFLICT / INCOMPLETE`：

- 开头把发现、构成、激活和更新都称为 G2 的五部分，会吞入 G1/G5/G7 的独立 truth owner；
- 逐条款状态若成为唯一 relation 内核，会弱化 V2 并列的 `AgentExecution /
  RelationEpisode / RelationEcology` 和原生机制身份；
- “开放缺口主要只在无中心环境”缩窄了 V2 的开放 schema、局部私有世界与低频长尾前提；
- 统一理解硬门把“允许理解、主体实际理解、制度构成、Principal Acceptance”重新合并。

最小修订是保留 Pro 的五段 lifecycle，但明确 owner：

```text
G1 candidate/path discovery
G2 relation language + constitution
G5 action-time Authority/Commitment/Reservation
G6 Effect/Adoption/Acceptance
G7 drift/reopen
```

它们可共享事件，不共享一个正式 truth。

### T2

当前是 `ARCHIVAL_ANSWER_LEAKAGE_REPLAY`。Pro 的“生产事故临时访问”可作为新任务族提案，
不能代替 T2。下一实验必须构造 fresh `T2-BLIND-INPUT` 和独立 oracle；任何从已公开 v2
反推的 relation schema 都不是冷启动证据。

### T3

原 T3 只是执行资源清单，不是可评分 episode。Wave 009 虽把新建 world 明确标成
`SYNTHETIC_TASK_SPEC / EXECUTION_RESOURCE_REQUIREMENT_ONLY`，但继续使用 `T3` 名称容易产生
谱系混淆。应重命名为 `T3-SYNTHETIC-RESOURCE-SLOT-SKIN`，且永不回填原 T3 coverage。

### T4

当前仍是 synthetic。Wave 009 的 24-world 核心没有 private action sets、feasible relation
equivalence classes、错误无解、局部 column 或真实 stance；它主要检验已生成事件的
relation/authority non-implication。因此 `24/24` 不能支持 T4 的 R1–R3 或 formation recall。

### T5

parent-owned authoritative state machine、readback、idempotency 和 relation bypass 是一个
`VERIFIED_LOCAL_NEGATIVE_CONTROL`。它仍没有实际成熟平台、真实成本、vendor failure 或
迁移，所以只能证明当前 synthetic fixed-platform skin 能旁路，不证明现实 SaaS 采购已由
本实验执行。

### Pro 的三个任务族

制造业加急、生产事故临时访问和受控数据申请是合理候选 task skins，但当前正文没有提供
已完成 episode、owner dossiers、冻结 Authority、原始记录或可追溯 outcome。称为“真实任务
族”是 `OVERSTRONG`；准确状态应是 `PROPOSED_REAL-WORLD-DERIVED_TASK_FAMILIES /
SOURCE_EPISODES_NOT_YET_FROZEN`。

## 八、外部技术来源状态

`G2-return.md` 中的技术判断没有可重建的 claim-source mapping。以下主张在本审计中统一为
`UNRESOLVED_SOURCE`：

- A2A 的 Task、Cancel、Artifact lineage 和授权边界；
- ARD v0.9 的 draft 状态与完整能力范围；
- FIPA Contract Net 的 binding semantics；
- WS-Agreement 的 negotiation/security 非目标；
- CMMN/BPMN、commitment/BSPL 的精确覆盖；
- VC/OAuth/OpenID 的规范边界；
- HIPAA、研究知情同意和公共采购制度的具体构成要求；
- 2026 negotiation/principal-loyalty benchmark 的结果。

这不阻止把相应技术作为 baseline 候选；在进入正式实验设计或稳定主张前，必须补回官方文档
或原始论文 URL、版本/日期、精确支持句与 claim ID。产品能力、标准表达力与端到端任务闭合
必须分开。

## 九、建议的最小下一实验

不要直接扩成 Pro 的 90-case 两阶段计划，也不要把现有 24-world 再换皮扩容。先运行一个
`G2-O1 OWNER-EVIDENCE + OPEN-SCHEMA DISCRIMINATOR`，目标是同时击穿 owner oracle、预编码
schema 和架构混淆。

### 1. 任务与分母

- 4 个 fresh T2-blind worlds：参数变化/真实 schema change、理解/误解、current/stale
  stance；
- 4 个 fresh T4-held-out worlds：column absent/withheld、局部异议、relation-level coupled
  constraint；
- 2 个 T5 platform-direct controls；
- 2 个相同任务的 Authority-topology pressures：shared institution / plural authorities
  with partition or equivocation。

共 12 个 world，先求分类和因果清楚，不报告现实频率。

### 2. truth-owner 分离

- world/schema author；
- 每个 Principal 的独立 actor/key/local view；
- institutional constitution evaluator；
- private-column oracle；
- Authority evaluator；
- target/Acceptance owner；
- method implementer。

任一角色不得同时生成全部 owner acts 和最终 truth。fixture 中删除可直接读取的
`relation_valid`、`material_change`、`opposition_preserved=true`。

### 3. 实验臂

- structured human institution；
- equal-envelope authority-aware strong center；
- actual mature-component composition；
- signed replicated state；
- 只在前三者留下稳定断点后加入的 relation candidate。

所有臂使用相同 Principal actors、local-oracle API、Authority endpoint、披露预算、时间与
task Q；strong center 完整解决就是正向结果。

### 4. 首要指标

- institutionally constituted / owner-understood / owner-claimed / action-authorized /
  activated 分轴真值；
- schema-change detection 与 false reopen；
- private-column feasible-path recall、false infeasible 和 policy-undiscoverable；
- provenance/opposition round-trip；
- stale stance、controller substitution、revocation、duplicate reservation；
- central/replicated 在 partition/equivocation 下的状态分叉与恢复；
- lifecycle cost，不把全体 Unknown 或 global stop 当胜利。

### 5. 双向判伪

- 若 equal-envelope strong center 或成熟组合在两个任务族、open-schema holdout、真实 owner
  actors、迁移与攻击中完整通过，则 G2 在该作用域应落为组合配置/conformance profile；
  不新增机制。
- 若它们在相同合法观察与 Authority 下稳定失败，而人工或 candidate 不增加 hidden truth、
  owner oracle、披露或预算却跨任务与迁移通过，才建立精确 residual。
- 若差异只在 partition、equivocation 或无共同 trust root 出现，只保留窄域同步/证据机制；
  不把“分布式”升为 G2 身份核心。

## 十、最终结论

G2 Pro 返回不是“证明通爻需要新协议”的文本；它最有价值的部分恰恰是把成熟制度、强中心和
零新增协议放回正解集合，并用构成动作攻击文本共识。这些应吸收。

但当前最承重的三项主张仍需降级：

1. `逐条款构成规则 = G2 完整内核` → `一种待保真检验的 RelationVersion 表示`；
2. `成熟组合已经完整解决` → `在明确前提下 candidate-complete，尚无合格端到端运行`；
3. `2×2 可决定是否需要分布式协议` → `需拆分构成语义、Authority topology 与 state
   placement 后再检验`。

本地 Wave 009 的准确状态继续是：

```text
B0/B5:
  VERIFIED LOCAL SIGNED-EVIDENCE CONFORMANCE
  24/24 on frozen structured worlds

NOT VERIFIED:
  independent Principal understanding
  independent owner stance
  open schema formation
  private column recall
  actual mature-product composition
  real T2/T3/T4
  V1/V2 general solution
```

因此，`G2-return.md` 与 `G2-final.md` 可作为候选理论、反例和实验素材，不能改正式状态、
NOW 或 PROGRAM，也不能把 B0/B5 的局部绿灯登记为关系已由真实主体构成。
