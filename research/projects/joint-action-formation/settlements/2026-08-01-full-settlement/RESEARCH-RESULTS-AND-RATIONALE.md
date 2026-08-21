# 通爻共同可行动性研究：结果、动机与证据边界总账

日期：2026-08-01  
状态：`CURRENT BEST SYNTHESIS / HISTORY PRESERVED / NO PRODUCT-COMPLETE CLAIM`

## 0. 读法与声明强度

本文把下列状态严格分开：

- `ESTABLISHED_DISTINCTION`：多轮材料和反例都要求保留的现实区别；
- `SUPPORTED_SCOPED`：在明确合成或本地数字条件下得到支持；
- `DESIGN_CANDIDATE`：结构已经提出，但尚未在合格任务中完整运行；
- `INVALIDATED`：评价器、输入、真值或归因被证明不成立；
- `UNKNOWN`：问题重要，但当前证据不足；
- `NOT_RUN`：只有协议、任务包或实现准备，没有实际结果；
- `REAL_WORLD_UNVERIFIED`：本地或合成结果不能外推到真人、组织、生产或长期净值。

文中“结果”包括改变设计的负结果、Unknown 和被纠正的历史结论。文件、代码、测试、哈希或
Agent 返回只有在改变问题判断、产品行为或证据可靠性时才进入结果账本。

## 1. 原始目标和产品对象

### 1.1 原始研究对象

最初 Problem v0 把研究对象定义为：多个不可互相替代的 Principal 世界之间，一项原本不存在、
不可行或不可判断的联合行动关系怎样被构成，并获得规范效力和现实效力。分析单位是一个有版本
边界的跨 Principal 关系形成与运行 episode，而不是单条消息、一次模型调用或孤立任务完成。

来源：

- `problem/v0.json` 第 7--24 行；
- `problem/v1-candidate.md` 第 12--50 行；
- `problem/v2.md` 第 28--44、104--114 行。

目标状态一直是：

```text
局部世界、未知条件和候选可能性
→ 必要主体能够理解、修正或拒绝
→ 条件和关系得到形成
→ 能力、权威、承诺和资源分别成立
→ 精确行动被执行
→ Target 世界产生可读回 Effect
→ 相应主体分别 Adoption / Acceptance
→ 成功路径可编译，失败或漂移时可恢复或局部重开
```

### 1.2 最终产品原本是什么

产品不是七个研究模块，也不是一套评测平台。历史材料共同指向一套“共同可行动性运行系统”：

- 用任务相关的最小充分上下文接住主体的 Intent；
- 发现既存路径，或创造伙伴、工具、权限、资源和表示等新条件；
- 形成一个可共同修改、可拒绝、可版本化的关系 episode；
- 把人的判断放在偏好、价值冲突、风险、责任和例外处；
- 把 ActionAttempt、Effect、Adoption、Acceptance 和 Settlement 分别交给相应事实源；
- 把稳定 episode 编译成低成本平台、流程或中心路径；
- 新差异出现时只重开受影响部分。

V2 明确说明，有界机制生态只是研究怎样组织，不是产品要服务的对象。产品真正服务的是行动路径
的发现、关系构成、执行、验收、沉淀和重开。

### 1.3 一个仍需显式处理的范围接口

V2 把上游怎样感知、推断、编译或生成 Intent 排除在核心研究对象外；协调接口从收到 Intent 后
开始。近期 PT-001 又从“模糊目标”开始。因此必须保留两层：

```text
产品入口层：模糊目标 → 主体确认的合格 Intent
                         ↓
V1/V2 核心：Intent → 可执行、可验证、可接受、可重开的 RelationEpisode
```

入口层可以进入最终产品，但入口评测不能替代核心问题的完成证据。相关纠正见
`TASK-TRUTH-CORRECTION-002.md`。

## 2. 最初的产品优先级与 v1.2 决策程序

### 2.1 P0 产品本身就是实验装置

更早的产品规划没有要求等待协议研究完成后再上线。第一版应先像正常业务一样运行，以规则粗排、
人工推荐、真实状态记录和升级预留为 P0；后续机制只有在同一任务上带来可观察改善时才接管。
“协议阻塞产品”被明确视为失败。

这意味着：

- 产品不是研究之后的包装；
- 真实请求、人工处理、拒绝、结果和复用成本本来就是研究数据；
- 不能为了等待一个完整理论而推迟最小可用产品；
- 也不能把研究 runner 当成 P0 产品。

来源：`research/projects/a2a-reconstruction/02_derived/zip-text-search-corpus/files/25/`
`25350d6d0261daacd72fba43fb05c46a7dce628e990efaeba8852fa6ad0d9253.md`。

### 2.2 v1.2 曾经已经诊断过一次相同漂移

`00_RESEARCH_RESET_v1.2.md` 的核心诊断是：研究投入与待决设计问题错位，大量工作证明了不会
改变设计的结构，而产品与架构顺序仍缺少判别证据。它建立的唯一开工门是：是否存在一个合理的
反向结果会改变系统设计、产品形态、适用范围或研究主张；若没有，该工作只能作为 CI、实现验证
或档案校准。

当时明确停止或降级的内容包括：新增大样本合成生成器、与同一形式定义共享 ground truth 的
大样本、常识性并发/缓存模拟、只验证自身字段的 replay，以及不卡住现实决策的新术语。

### 2.3 Q1--Q6 原始决策门

| 决策门 | 要决定什么 | 最便宜判别 | 当前真实状态 |
|---|---|---|---|
| Q1 | 产品先走中心语义控制面，还是立即投入跨域运行层 | 同 Mandate、信息、查询、Effect Gate 下的公平强中心真实模型 | `NOT_COMPLETED_AS_ORIGINALLY_DEFINED` |
| Q2 | 用户维护显式 Mandate，还是系统内部对象+关键确认 | 3 名真实 OPC、1--2 个真实事项 explain-back | `NOT_RUN_WITH_REAL_PARTICIPANTS` |
| Q3 | formation operator 是核心引擎，还是记录/辅助 | 一个 7--14 天、低风险、可撤销真实事项，冻结前态、operator、消融、Effect | `NOT_RUN_AS_REAL_SINGLE_CASE` |
| Q4 | Router 可自动判断，还是人机清单 | 原始公开材料冷启动盲判与独立 gold coding | `NOT_COMPLETED_WITH_INDEPENDENT_GOLD` |
| Q5 | 成功路径编译复用是否产生现实净值 | Q3 成立后第二、三次重复事项 | `BLOCKED_BY_Q3` |
| Q6 | 首发市场的对抗边界 | 低对抗、可撤回、存在声誉/担保的边界观察 | `OPEN` |

来源：`Towow_v1.2_Decision_Program/00_RESEARCH_RESET_v1.2.md` 第 49--96 行；未完成状态见同目录
`README.md` 第 15--20 行。

## 3. 已经形成的核心问题判别力

这些是研究最稳定、最值得进入产品约束的成果。

### 3.1 搜索、协调与构成必须区分

`ESTABLISHED_DISTINCTION`

- 找到已存在路径是 discovery；
- 改变工具、权限、伙伴、资源或现实条件，使路径首次出现，可能是 formation；
- 降低原始价值、改写 Q 或遗漏必要主体是 problem transformation；
- 自然语言变多、消息轮次增加或结构更完整，不等于行动空间改变。

去掉这一区别，产品会把检索命中、澄清文本或目标缩水写成形成成功。

### 3.2 Agent Entity 与 Principal 必须区分

`ESTABLISHED_DISTINCTION`

可认证的 Agent、账号、模型或执行者不等于有权表达、授权、接受或承担后果的 Principal。Intent
生成者、受益者、受影响者、决定者和执行者都可能不同。

去掉这一区别，模型和 controller 会替主体宣布偏好、授权、承诺或 Acceptance。

### 3.3 Capability 与 Authority 正交

`ESTABLISHED_DISTINCTION`

模型更强、工具调用成功、历史 operation 成功或本次 probe 通过，都不能扩大 Authority Envelope。
反过来，有权也不证明具体 operation 能完成。

产品含义：能力资格化与授权/承诺必须是两条不同证据路径，并在 attempt 时重新汇合。

### 3.4 Attempt、Effect、Adoption、Acceptance、Settlement 不互推

`ESTABLISHED_DISTINCTION / STRONGEST ENGINEERING RESULT`

R5.2 的真实 Harness 场景中，naive 终态标签曾在 17 个场景中错 10 次，直接促成 Effect Gateway
和 Target readback。后续多轮合成实验又反复证明：producer 完成、消息 ACK、workflow green、
相同终态和 controller 文本都可能冒充更高层状态。

产品含义：完成状态必须由相应 Target/owner/acceptance source 重建；UI 不能用一个 success
布尔值压平整条现实效力链。

### 3.5 Formation 与 compiled runtime 是两种运行制度

`SUPPORTED_AS_DESIGN / REAL_NET_VALUE_UNKNOWN`

开放形成期处理未知角色、条件、关系、权威和例外；稳定路径应编译为低成本确定性运行。新差异、
撤销或证据失效才重开必要部分。

这不是要求所有任务都走 formation。相反，简单稳定任务应直接旁路。尚未完成的是 Q5：真实第二、
第三次运行是否真的降低高认知分钟、披露、错误和恢复成本。

### 3.6 权威拓扑比网络拓扑更承重

`SUPPORTED_SCOPED / GLOBAL CLAIM UNKNOWN`

分布式进程不自动产生不可代行权威；中心进程也不自动越权。决定机制结构的是信息能否合法集中、
是否存在可信 Hub、谁能作出当前决定、Target 在哪里消费撤销和谁拥有 Acceptance。

产品含义：中心、平台、人类和跨域路径应按 episode 条件路由，而不是预先选阵营。

## 4. 形成的系统与产品设计能力

下列对象均已产生明确设计作用，但证据强度不同：

| 设计能力 | 解决的精确问题 | 当前身份 |
|---|---|---|
| Intent/goal 的来源与确认状态 | 阻止入口相关性穿透为主体认领 | `DESIGN_CANDIDATE`；上游范围需显式 |
| task-relative projection | 不复制完整局部世界仍能贡献任务相关线索 | `SUPPORTED_SCOPED_LOCAL_SYNTHETIC` |
| typed Unknown/Refuse/Stale/Impossible | 阻止未发现、拒绝和不存在混淆 | `SUPPORTED_AS_REQUIRED_SEMANTICS` |
| reciprocal probe + candidate handoff | 把单边可能性推进为双方当前可继续判断的候选 | `SUPPORTED_SCOPED`; 现实跨主体未验证 |
| RelationVersion / shared proposal | 保存 material change、局部异议和当前 head | `CONDITIONAL`; one-shot 是否足够需任务判断 |
| scoped Mandate / delegation / reservation | 分开授权、承诺和稀缺资源 | `SUPPORTED_SCOPED`; 法律/真人权威未验证 |
| prospective capability qualification | 在具体 executor/environment/version/permission/resource 下预测可依赖性 | `PARTIAL / REAL_CALIBRATION_UNKNOWN` |
| target-native receipt/readback | 阻止 producer/controller 自报业务 Effect | `SUPPORTED_SCOPED_DIGITAL` |
| completion/Acceptance gate | 缺精确 Effect 或相应 Acceptance 时不显示完成 | `CORE_PRODUCT_REQUIREMENT` |
| dependency/defeater reopen | 变化后阻断、恢复或只重开受影响部分 | `SUPPORTED_SCOPED`; 隐藏依赖和真实净值 Unknown |
| compiled stable path | 将形成结果变为低成本重复运行 | `DESIGN_CANDIDATE`; Q5 未运行 |
| Router | 按 episode 条件选择 direct、中心、人类、跨域或组合路径 | `DESIGN_CANDIDATE`; Q4 未完成 |

NAC 保持独立研究身份。它当前只处理“已形成投影怎样表示、比较、渐进披露和迁移”的有界切片，
不能替代上游未表达机会生成、Authority、Effect 或 Acceptance。H1 的表示实验不能支持整个发现
问题；详见 `TASK-TRUTH-CORRECTION-001.md` 第 125--136 行和 NAC 七件档案。

## 5. 真正改变设计的早期实验

### 5.1 R5 / R5.2

`SUPPORTED_SCOPED / DESIGN_FLIP_OBSERVED`

- outer success、producer bytes、终态标签与 canonical Effect 被证明不同；
- authoritative readback 从附属日志升级为完成判定前提；
- 能力主张开始绑定环境、权限、资源、观察与恢复；
- 部分任务中 least-privilege central 路径优于更重的协调结构。

### 5.2 R5.4

`MIXED / CENTRAL_BASELINE_TRANSPORT_FAILURE_PRESERVED`

- 不同权威角色的拒绝与 countercondition 会改变候选规范；
- 更多消息轮次不自然形成能力；
- `AcceptedOriginalValue=0` 与规范增量必须同时保存；
- 强中心的长输出 transport 失败使比较不完整，不能把缺席基线写成其他路径胜出。

### 5.3 R5C

`SUPPORTED_SCOPED`

- adopted→revoked→offline→recovered 的跨域状态被建模和重放；
- producer-only 与 wrong-authority 路径不能闭合；
- formation 与 holdout 分离；BLOCK/COUNTER/UNKNOWN 历史不被最终 PASS 删除；
- 支持“边界形成后，中心确定性执行可以足够”的限域结论。

历史结果入口：`research/projects/a2a-reconstruction/00_orientation/RESULTS_MAP.md`。

## 6. 七母线 Wave 001--025 的综合结果

逐波原始动机、结果和来源见三个附录。这里仅保留会改变产品理解的总结果。

### 6.1 Wave 001--004：从问题扫描到本地候选链

- Wave 001 首先发现任务分母不合格：T2 泄漏解法，T3 只有资源清单，T1/T4 缺独立实例，T6
  没有 base trace。该波只能导航，不能给 coverage。
- Wave 002 在 T1-HW-A 上得到公共目录 `0/8`、本地投影 `1/8`、组合 `5/8`。重要发现不是数字
  本身，而是路由、局部变化/拒绝、互惠确认和候选交接必须共同闭合。
- Wave 003 提出 `local trigger → projection → routing → reciprocal probe → candidate handoff`；
  T1 首个候选虽找对 3/3 机会，却把授权冒充已执行，只过 1/8；手写 completion 被撤回。
- T4 本地联合投标得到 `0.60 / PARTIAL`，暴露风险分配、审计范围和签署 Authority 未闭合；
  mutation 部分成立，migration 未运行。
- T5 前两版 evaluator 均出现假绿；第三版才支持简单平台任务 direct/轻封装的有界结论。
- Wave 004 实现本地 controller、recipient store readback 和 execution receipt，支持本地合成候选
  链，但 Relation、Commitment、跨域 Authority、业务 Effect 和 Acceptance 仍未建立。

产品意义：发现链的前半段和“授权不等于执行”获得了参考实现，但没有形成 RelationEpisode。

### 6.2 Wave 005--009：独立 truth、分域证据与七线重新分工

- fresh held-out world、独立 truth/evaluator 和分域 receipt 逐步建立，暴露 post-oracle 修补、
  同进程自读回、公开 seed/private key 和表面标签计费等假绿。
- G1 的局部强中心/router 在 cooperative、non-reflective、逻辑 API 条件下可以同等解决指定
  discovery 问题；不支持开放世界一般结论。
- G2+G5 在本地 crossed-square 中证明 durable relation 与当前 permission 可独立变化；一次
  permit 不必先有持久关系，持久关系也不代表当前允许。
- G3 把 reachability 拆成 exists/actual/effect-robust/safe-robust/terminal-robust；合法拒绝可以
  使 Effect 不可达而安全性成立。
- G4/G6/G7 明确必须分别评价执行前 reliance、Target Effect ladder 和 affected reopen；但 T6
  缺合格 base-run，不能报告完整覆盖。

产品意义：七条线的 native truth owner 被澄清；最强结论是“同一 episode 不能由一个 success
状态承载”，而不是新模块数量增加。

### 6.3 Wave 010--020：共同 world、执行 kernel、Effect 与恢复

- Wave 010 把跨线 episode 输入、输出和禁止蕴含收敛为候选合同，但仍是设计，不是现实结果。
- Wave 013 建立一个共同合成 world；在经过 label/hash/argv 等多次泄漏修复后，只支持 E1
  success 与 E5 bounded refusal 的局部状态，不支持全部 case。
- Wave 014 causal twin 证明相同 Target state 可以由候选 actor 或 helper 造成；Target 原子提交+
  readback 能在该数字边界内区分直接 actor，不能证明全局物理因果。
- Wave 015 建立共享 runner 基础，并暴露“各组件分别绿色但 schema/truth owner 不可组合”的问题。
- Wave 016 支持 ACK 丢失下已提交 reconcile 与未提交 safe retry 的一对数字任务。
- Wave 017 证明在合法统一 Authority 域，平台一次 native action 可以完整解决指定简单任务；产品
  应旁路开放形成。
- Wave 018 支持 revoke 后 bounded reopen、替代方 rediscovery、owner current head、Target
  readback 与双 Acceptance 的合成组合；早期内存 ledger/WAL artifact 被拒绝。
- Wave 019 支持 workflow+HITL 在精确 counter、owner response、reservation 与 commit-time gate
  条件下形成本地合成 episode；不证明物理 Effect 或真人权威。
- Wave 020 支持 controlled termination 后通过签名 capsule、Target receipt、epoch fence 恢复
  若干 postcondition；不支持不可预告硬崩溃、跨机器或生产保证。

产品意义：执行、Target readback、bounded refusal、ACK-lost、revoke/reopen 和迁移获得一组可
复用数字 kernel，但它们从未在同一个新的完整用户事项中共同闭合。

### 6.4 Wave 021--025：公平比较、假绿与设施漂移

- Wave 021 冻结多类 arm 的公平比较合同，但实际比较运行始终为 0，winner 始终为 NONE。
- Wave 023 证明静态 validator 可接受 payload oracle、声明/实际 Authority 不一致、隐藏调用、
  post-grader trigger 和未冻结 executable/world；开发 manifest 不能冒充实际运行。
- Wave 024 支持一个 Target 消费版本化 Authority fence 的局部并发例，同时证明远端撤销而 Target
  未消费 fence 时不能强行判成功/失败；该波因固定顺序和同权限通道不具备全臂盲比较资格。
- Wave 025 继续修复 runner、evaluator、feature、classifier、数学和 receipt gate，确实暴露
  更多假绿；但后半段逐渐失去具体产品决定，设施建设成为连续主目标。

当前决定：Wave 025 保留为按命名产品决定调用的内部工具。通用 3,200、C01--C05、MODEL-INPUT、
全臂 tournament 和自动 research promotion/deletion gate 未完成，也没有当前启动理由。安全相关
部分另交安全人员；本研究不作安全保证。

## 7. 被纠正、失效或必须保留的负结果

### 7.1 任务真值纠正

- T2 是答案泄漏 replay，必须拆成 blind input 与独立 oracle；
- T3 的 R7 来源只是未来执行资源清单，没有 S0、角色、资源、动作或 Authority postcondition；
- T1/T4 只是合成任务规格；
- T6 只是 mutation spec，未有合格 base episode；
- V0 一度被错误当作基线能力边界，后恢复为原始价值与不可接受底线，基线另设 BE0。

这些纠正不是措辞问题，它们取消了此前可能出现的 coverage、现实任务和迁移完成主张。

### 7.2 反复出现的假成功类型

1. 方法标签或 manifest 声称执行，真实动作没有发生；
2. controller 代 owner、Authority、Target 或 Acceptance source 自报；
3. solver 看到了 case label、hash、argv、semantic case、private keys 或 scorer depth；
4. 相同终态由 helper、预存在状态或其他 actor 造成；
5. receipt 声称 current，但 owner current head 已变化；
6. ACK 丢失后重复执行，产生第二 Effect；
7. WAL 主文件、旧 artifact 或同目录副文件让冻结包不完整；
8. 组件各自通过，但接口语义和 truth owner 不一致，无法组成 episode；
9. 大量样本继承错误的 cost label、真值或 generator；
10. evaluator 只检查格式或自洽，没有检查用户目标、Target 和 Acceptance。

### 7.3 研究方法漂移

v1.2 已经警告不要让合成规模和形式工作取代设计判别。Wave 025 后半段再次复发。当前必须保存的
结论是：评价设施只有在会改变一个命名产品行为、且更小任务证据不足时才升级；设施本身不构成
产品进展。

## 8. 七条母线当前真实状态

| 母线 | 已经推进 | 当前最承重缺口 | 不能宣称 |
|---|---|---|---|
| G1 发现与边界 | projection、typed state、目录/本地组合、fresh held-out、false wake 边界 | 真实动态主体、未表达机会的现实增益、从 handoff 进入完整 episode | 一般开放世界发现已解决 |
| G2 问题与关系构成 | relation/permission crossed square、counter、owner response、版本候选 | 真人 explain-back、material change 净收益、真实共同认领 | RelationVersion 必需或产品可用 |
| G3 可能性形成 | discovery/condition creation/problem rewrite 分离、QHM 局部结果 | 一条真实 causal formation、operator 消融、目标保持 | formation 引擎已被证明 |
| G4 能力兑现 | operation-specific probe、readiness/expiry/recovery 设计、局部 holdout | 现实前瞻 calibration、false commitment、跨环境迁移 | capability 可稳定依赖 |
| G5 权威与规范 | owner-native decision、scoped grant、reservation、current head、Target fence 局部结果 | 真人/法律 Authority、跨域时序、执行时消费 | 任意部署结构具备规范充分性 |
| G6 现实效力 | Effect ladder、Target readback、causal twin、completion gate 局部结果 | 真实业务/物理 Effect、真人 Acceptance、长期 dispute/settlement | 本地数字 receipt 等于现实完成 |
| G7 运行与演化 | ACK-lost、revoke、alternative、epoch migration、bounded reopen 局部结果 | Q5 第二/三次真实复用、隐藏依赖、全生命周期净值 | 编译复用已经产生现实收益 |

## 9. PT-001 当前材料的结果与准确身份

2026-08-01 已产生：

- 产品旅程重建；
- N0--N12 机制组合候选；
- D0--D10 评测必要性地图；
- 三个合成任务真值候选；
- 六类 D1/D2 产品行为；
- D1/D2 最小评价合同。

这些材料的正确身份是：

```text
产品入口与完整 episode 集成前的 DESIGN CANDIDATE
NOT_YET_RUN
NO COVERAGE
NO REAL EFFECT
NO ACCEPTANCE
```

其价值在于：

- 明确入口层与 V1/V2 核心接口；
- 把目标偷换、拒绝擦除、过度披露、目录 no-match、假 probe 和错误完成列为结构性阻断；
- 形成产品行为候选，而不是模型文风比较；
- 为一个完整 episode 提供可检查的前态候选。

其风险在于：若继续把 D1/D2 独立扩成任务库、arm 大赛或通用 benchmark，会再次替代原计划的
跨线集成。当前不应运行扩展性 D1/D2 研究；它只能随一个完整 episode 作为入口观察。

## 10. 为什么当时要做这些工作

| 工作家族 | 当时的正当问题 | 产生的有价值结果 | 何时变成浪费 |
|---|---|---|---|
| 问题与历史重构 | 防止近期输入覆盖完整问题和历史能力 | V0/V1/V2、39 能力矩阵、七条 native truth | 只做术语统一，不改变产品判断 |
| 公开方案与强基线扫描 | 检查我们是否遗漏更简单的完整解 | 暴露两个承重接口、direct 路径和条件路由 | 变成技术目录或为差异而找差异 |
| hidden world / oracle | 区分真正发现、答案泄漏和不可发现 | 发现链的假绿与 disclosure 边界 | evaluator 与 generator 共用 truth，或无限扩样 |
| controller / runner | 让“建议执行”变成真实本地动作和 readback | 授权≠执行、ACK-lost、idempotency 等 kernel | runner 完善不再改变产品机制 |
| receipt / Target ledger | 防止 producer/controller 自证 Effect | Target readback、current head、causal twin | receipt 数量和哈希替代现实目标 |
| relation / authority paired worlds | 判断关系是否需要物化、谁能决定 | relation 与 permission 可独立变化 | 没有 downstream 行为差异仍扩本体 |
| formation / reachability | 判断何种干预真的创造路径 | 发现/形成/目标改写区分、QHM 局部结果 | 不进入真实 operator 与 Effect |
| failure / migration replay | 判断成功路径能否重复和恢复 | revoke、ACK-lost、alternative、epoch 等局部能力 | 没有 base episode 却无限造 mutation |
| fairness / blind qualification | 防止方法偷看答案或 controller 代做 | 多类 runtime 假绿被揭露 | 没有产品决定仍扩成通用设施 |
| PT-001 | 把分散七线重新串回用户产品链 | 入口、旅程、组合与评测边界显式化 | 停在 D1/D2，不进入完整 episode |

## 11. 当前完成与未完成

### 已经可以作为产品约束继承

- 原始目标、必要主体和不可接受底线不得被静默改写；
- 用户和其他 Principal 可以拒绝、保持 Unknown、counter、撤销和退出；
- 简单稳定任务必须旁路复杂形成；
- 发现候选不等于能力、意愿、关系、授权或承诺；
- capability、authority、commitment、reservation、execution 分别建立；
- Target Effect、Adoption、Acceptance 分开；
- attempt 前需要 current authority/resource gate；
- ACK 丢失先 readback/reconcile，不能盲 retry；
- 历史 Acceptance 不因后续失效被改写；
- 稳定路径应编译，但只有实际复用证明其净值后才能称产品核心。

### 尚未完成的原计划

- 一个真实运行、低风险、可撤销、两个独立 Authority locus 的完整 RelationEpisode；
- Q1 的公平真实模型决策；
- Q2 真人 explain-back；
- Q3 causal formation operator 与消融；
- Q4 原始材料 blind Router gold；
- Q5 第二、第三次复用净值；
- 一个 P0 产品壳真实承载目标、提案、决定、执行、Effect 和 Acceptance；
- 两个异质任务族和留出变体上的完整集成；
- 现实长期成本、维护、迁移、退出和商业净值；
- 任何通用安全保证。

## 12. 当前结论

长期研究并非没有产出。它已经把问题从“Agent 怎样匹配/通信”推进为一套能够识别目标、关系、
能力、权威、现实 Effect、Acceptance、复用和重开的完整判别框架，并产生多项有界数字 kernel。

但原始产品规划尚未交付。反复出现“下一步”的根因，是决定性 Q1--Q5 和完整 episode 被局部合成
研究与评价设施持续替代。下一阶段若仍按 D1→D9 分段扩张，就会再次重犯。

因此当前研究状态应写为：

> `PROBLEM_AND_SCOPED_MECHANISM_PROGRESS_SUBSTANTIAL / END_TO_END_PRODUCT_EPISODE_NOT_COMPLETE`

后续执行只以 [ROOT-NEXT-PLAN.md](./ROOT-NEXT-PLAN.md) 为主研究者当前提案；在用户确认前保持
`PAUSED_FOR_ALIGNMENT`。
