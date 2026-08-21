# PT-001 产品链评测设施必要性地图

日期：2026-08-01  
状态：`INDEPENDENT_REVIEW / PRODUCT-ALIGNED / NO_SECURITY_CLAIM`

## 结论

评测设施确实有一组不可删减的产品内核，但它不是 Wave025 的通用盲比较平台。

对当前 `PT-001-FUZZY-RESOURCE-COLLABORATION` 候选，真正必要的是：

1. 先取得一个有完整前态的具体用户任务，而不是继续把 `R7_RESOURCE_REQUEST.md` 当作现实任务；
2. 在发现与披露阶段，用 fresh hidden-world holdout 区分真实发现、答案泄漏、虚构 probe/receipt
   和目标改写；
3. 在协商、授权、执行和验收阶段，让 owner、Authority、Target 与 Acceptance 的原生事实源
   分开，不能让 controller、模型或界面替它们自证；
4. 用同一真实 base episode 的拒绝、counter、撤销、ACK 丢失和漂移 replay 判断是否安全重开；
5. 用用户任务结果、披露、等待、人工判断、错误、恢复和重复成本共同决定产品机制。

这些设施直接阻止已经发生过、会改变产品设计的假绿，因此是 `CORE_NECESSARY`。相反，通用
3,200 样本、C01--C05 classifier、MODEL-INPUT、完整 byte-level 数学包装和自动研究状态晋升/
删除门，目前没有绑定到一个需要它们才能作出的产品决定，结论为 `NOT_JUSTIFIED_YET` 或
`CONDITIONAL`，不得无条件续建。

本审查没有实施网络、容器、主机隔离、权限绕过、真实利用或其他安全验证。凡涉及这些能力，
统一标记 `SECURITY_REVIEW_REQUIRED / NO_SECURITY_CLAIM`。

## 一、任务真值边界

### 1. 当前链路不是“T1 加一个已有 T3 现实任务”

`TASK-TRUTH-CORRECTION-001.md` 已确认：`R7_RESOURCE_REQUEST.md` 只是未来实验所需的案例数、
Principal、adjudicator、追踪期和保密资源清单；它没有请求的 `S0`、具体资源、角色、动作、
Authority 或后置状态。因此：

- 旧 T3 的 `ARCHIVAL_REAL_WORLD_TASK_DESIGN` 身份作废；
- 旧 T3.R1--R8 只能作为新任务的设计检查项，不能当 coverage 分母；
- 当前评测对象是 `T1 + 新构造的 PT-001 非标准资源协作产品任务候选`；
- `PT-001` 当前仅为 `NEW_SYNTHETIC_PRODUCT_TASK_CANDIDATE`，不是现实发生证据。

这不是文档措辞问题，而是第一项产品评测缺口：没有具体用户、真实模糊目标、真实资源 owner、
真实拒绝权和可观察后置状态，后续机制再严谨也只能证明在自造任务里可行。

### 2. 产品链的判定对象

本地图把链路重写为十一项会改变产品行为的决定：

```text
D0 任务是否真实、是否值得解决
→ D1 怎样澄清而不替用户改写目标
→ D2 怎样发现未表达机会并控制披露
→ D3 何时发起询问或互惠 probe
→ D4 是否、何时物化可修改的合作关系
→ D5 何时可把能力声明升级为可依赖承诺
→ D6 由谁同意、授权、预留和撤销
→ D7 由平台、强中心、委托执行者还是组合来执行
→ D8 何时可以宣称 Effect 与 Acceptance
→ D9 失败、拒绝或漂移后重开什么
→ D10 稳定路径是否值得编译和复用
```

评测设施只有在能够改变其中至少一个决定时才有产品价值。

## 二、设施语义先分开

为避免“删实验室”时误删产品真实性，也避免“需要收据”被扩张成通用收据平台，本地图采用
下列区别：

| 名称 | 本地图中的精确定义 | 不是 |
|---|---|---|
| 直接用户任务指标 | 用户是否仍认领原目标、是否愿意继续、是否完成、等待/询问/披露/人工负担 | UI 上的绿色状态或模型自报完成 |
| 独立 evaluator | 不调用 solver/controller 的总结，直接读取冻结任务真值和 owner/Target 原生证据作判断 | 第二个模型同意第一模型 |
| replay | 从一个实际 base episode 的冻结前缀注入拒绝、撤销、ACK 丢失、变化或恢复 | 自造一个相似故事重新跑 |
| 原生 receipt | 由事实 owner 在事件发生处绑定对象、版本、actor、scope、decision/readback 的证据 | controller 写的“owner 已同意”文本 |
| completion gate | 产品在缺 Effect/readback/Acceptance 时不得显示 `COMPLETED` | 自动晋升正式研究主张或删除历史证据 |
| byte determinism | 只有当签名、精确输入公平性或跨实现复算依赖同一字节时，冻结规范化字节 | 所有研究都必须进入 byte-level 数学系统 |
| statistics | 为随机、稀有或近似同分的产品差异给出足够不确定性界限 | 用大样本替代任务真实性、因果或 Authority |
| blind holdout | solver 未看到 task truth/期待答案的 fresh 任务或变体 | 已知答案任务上隐藏一个标签字段 |

## 三、逐产品决定的必要性审查

以下 verdict 判断的是“为当前产品决定建设相应评测能力是否必要”，不是提前判某个产品机制
必然采用。

### D0：先取得一个真实、具体、可拒绝的非标准资源任务

**产品决定**  
决定 `PT-001` 应解决哪一种真实用户困境、原始价值和不可接受底线；否则停止机制选型，继续
任务发现。

**直接用户任务指标是否足够**  
这里直接主体证据是首要 truth source：用户、资源 owner、受影响者分别确认 `S0`、目标、拒绝
权和成功条件。仅有研究者生成的任务文本不够；也不能用完成一个合成任务倒推现实需要。

**已经发生的假绿**

- PROGRAM 把 `R7_RESOURCE_REQUEST.md` 误登记为现实任务设计；逐字审计证明它没有任务前态。
- T2 原文已经含 counter、probe、v2 与裁决，若直接交给 solver 会把答案泄漏 replay 当冷启动
  能力。
- 多轮合成实验已有完整 schema、测试和 evidence bundle，但均明确不证明现实用户、法律
  Authority、物理 Effect 或真人 Acceptance。

**最小有区分力评测**

取得至少一个独立于 R7 清单的具体、低风险、可撤销资源请求，冻结：

- 原始模糊目标及用户不能接受的目标改写；
- 用户、resource owner、受影响者、执行者与接受者，不预设重合；
- 可请求资源、边界、时间、用途和最小现实后置状态；
- `REFUSE / COUNTER / DEFER / REVOKE` 的合法分支；
- 成功、保护性拒绝、诚实 Unknown 与问题改写的区分；
- 谁能给出 Effect readback，谁能给出 Acceptance。

第一份任务材料应先做 member-check，不需要通用 runner。

**设施需求**

| 设施 | 当前需要 |
|---|---|
| 独立 evaluator | `CONDITIONAL`：任务作者与用户/owner member-check 需分开；无需先写通用机器评分器 |
| replay | `NOT_YET`：先有 base task，再设计变化 |
| 统计 | `NO`：一个具体任务可以先决定是否值得进入产品实验 |
| byte determinism | `NO` |
| receipt gate | `NO`：此处需要来源记录，不需要自动状态晋升 |

**成本与停止点**  
成本是访谈、任务还原和 member-check，而不是代码。获得一个各方能认领、允许真实低风险动作且
Effect/Acceptance 可观察的 task v1 后停止任务规格扩建，进入 D1；若找不到，`PT-001` 保持产品
假设，不以更多合成评测补洞。

**Verdict：`CORE_NECESSARY`**

### D1：访谈式澄清、主动推断和已有上下文检索怎样组合

**产品决定**  
决定系统何时追问、何时提出可撤回假设、何时检索已有上下文，以及何时保持 Unknown，避免把
“少问问题”优化成替用户改写目标。

**直接用户任务指标是否足够**  
用户是否认领最终 goal/request 是主指标，但单看“最终得到一个请求”不足：系统可能偷看完整
答案、遗漏受影响主体、把底线改写掉，或靠高负担追问完成。还需记录纠正次数、错误假设、轮数、
目标保真和晚期返工。

**已经发生的假绿**

- T2 完整答案泄漏说明“模型生成正确 v2”可以完全不代表澄清能力。
- T4 候选把没有 Authority 证据的 risk allocation 和 audit scope freeze 写成“所有条件满足”。
- Wave013 中 label、manifest hash 和 parent argv 先后三次泄漏 case，均可让候选看似正确。

**最小有区分力评测**

在 D0 的同一任务上制作一个 `FUZZY-INPUT` 和 owner-private `TASK-ORACLE`：前者只含用户当时真实
可表达的信息；后者保留关键底线、可接受澄清、错误改写和必要角色。比较三种最小产品行为：

1. 只追问；
2. 先提出可撤回假设、再 member-check；
3. 检索已有许可上下文后再追问。

以目标保真、必要条件召回、错误假设、询问轮数、用户纠正负担和进入下一节点的比例决定组合，
不比较模型文风。

**设施需求**

| 设施 | 当前需要 |
|---|---|
| 独立 evaluator | `YES`：持有 task oracle，不能由澄清模型给自己判“理解正确” |
| replay | `YES, SMALL`：至少一项用户中途改目标/拒绝披露的变体 |
| 统计 | `CONDITIONAL`：先用少量异质任务；仅在两个交互策略近似同分时扩样 |
| byte determinism | `NO`：语义输入冻结和完整 transcript 足够 |
| receipt gate | `NO`：member-check 记录即可，不能自动推出授权 |

**成本与停止点**  
先做 3--5 个异质模糊目标，不建通用意图 benchmark。某组合稳定避免目标改写且询问/纠正负担不劣
于纯访谈后，先选为产品默认；只有新任务族出现系统性错误才重开。

**Verdict：`CORE_NECESSARY`**

### D2：目录/RAG、端侧投影、强中心推断与渐进披露怎样组合

**产品决定**  
决定发现链的默认路由：先用已声明目录与许可上下文，何时请求端侧 task-relative projection，
何时触发互惠发现，以及何时诚实报告不可发现。

**直接用户任务指标是否足够**  
“最后找到一个伙伴”不足。它不能区分：真正从未表达信号发现、碰巧命中已登记对象、读取了
private oracle、过度广播后命中，或制造了大量错误唤醒。至少还要看机会 recall、false wakeup、
累计披露、接收者/用途、拒绝保真、更新滞后与 honest-undiscoverable 校准。

**已经发生的假绿**

- T1 第一冻结 world 中目录 A=`0/8`、端侧投影 B=`1/8`、A+B=`5/8`；说明组合有价值，但不是
  完整解。
- HW-B 首个 solver 映射 `3/3` 机会，却只有 `1/8` requirement；它虚构了 disclosure route、
  reciprocal probe 和 event ID。
- controller 真实运行后 development score 为 `4/8`；只在看过 scorer 隐藏 depth/orientation/
  status 后改表示得到 `8/8`，该 V3 明确不是 blind evidence。
- Wave006 G6/G7 候选读取 semantic case/真值 label 和全部私钥后可直接制造高层成功。

**最小有区分力评测**

复用 E1 的思想，但缩到一个产品任务：由独立 world author 冻结 3--5 个 latent opportunity、
至少一个 decoy、一次撤销/更新、逐方 disclosure policy 和一个 policy 下不可发现的机会。solver
只看 method-visible event。fresh holdout 上比较：

- catalog/ARD/Agent Card；
- 本地规则或模型生成的 task projection；
- 二者组合；
- 必要时再加受控 probe。

评价器必须从真实披露日志读取 recipient、purpose、retention、refusal，不能接受候选自报。产品
决定以 recall--false wakeup--disclosure 前沿为准，不要求单一全局冠军。

**设施需求**

| 设施 | 当前需要 |
|---|---|
| 独立 evaluator | `YES, CORE`：latent truth 与 disclosure policy 必须对 solver 隔离 |
| replay | `YES, CORE`：至少覆盖 update、withdraw、stale directory |
| 统计 | `CONDITIONAL`：需要足够机会数估计漏检，但不是通用 3,200 blind population |
| byte determinism | `CONDITIONAL`：只有公平比较要求各方法收到完全相同公开 packet 时冻结 bytes |
| receipt gate | `YES AS PRODUCT EVIDENCE`：实际 disclosure/ACK receipt；`NO` 对自动研究晋升 |

**成本与停止点**  
一个 fresh task family 加一个撤销变体即可先决定默认组合。若 A+B 已满足用户底线，停止增加
classifier；若 residual 集中于未表达机会或合法互惠 probe，再为该 residual 建 D3，不把全部
发现问题交给 Wave025。

**Verdict：`CORE_NECESSARY`**

### D3：何时请求更多信息或发起互惠 probe

**产品决定**  
决定在目录/投影不足时，是继续询问用户、向候选方发最小 purpose-bound probe、转人工，还是
保持 Unknown/退出；probe 成功是否足以进入合作提案。

**直接用户任务指标是否足够**  
对方实际回复、拒绝或不回应是最直接指标；solver/controller 声称“probe 已完成”不够。即使
probe 成功，也只建立精确 capability/interest 事实，不能自动建立持续关系、Authority、Effect
或 Acceptance。

**已经发生的假绿**

- T1-HW-B 在没有 controller executor、receipt issuer 或执行日志时一度手写 completion JSON，
  后被撤回。
- Wave004 证明 recipient store readback 后才签发 receipt 能关闭四类本地攻击；同时明确
  `CROSS_AUTHORITY_REALITY_UNKNOWN`。
- T2 disclosure controller 的 `8/8` 只说明合法 next-step probe 被忠实构造；真实 probe 仍是
  `NOT_RUN`，Effect 等均未发生。

**最小有区分力评测**

在真实或可认领的低风险任务上只运行一个最小 probe：

- 明确 recipient、purpose、scope、expiry、允许的答复与保存期；
- 对方原生给出 `ACK / COUNTER / REFUSE / DEFER`；
- 发送方不得从发出请求推断对方已接收或同意；
- 删除/篡改 recipient readback 后必须回到 Unknown；
- probe 结果只能进入候选提案，不能直接升级为授权或完成。

若现有平台本身提供权威当前状态，直接读取平台状态是更简单正解，不应强制 probe。

**设施需求**

| 设施 | 当前需要 |
|---|---|
| 独立 evaluator | `YES`：直接读 recipient-native response/readback |
| replay | `YES, SMALL`：重复请求、过期和撤回 |
| 统计 | `NO`：一个 falsifying branch 已可决定 receipt 是否必要 |
| byte determinism | `CONDITIONAL`：签名/哈希绑定时只冻结该消息的 canonical bytes |
| receipt gate | `YES AS EVENT EVIDENCE`；通用 promotion/deletion gate 不需要 |

**成本与停止点**  
完成 `ACK + REFUSE/DEFER + stale/duplicate` 三类分支即足以决定产品状态机。不得为它建立通用
probe qualification 平台。任何跨权限域不可伪造或网络隔离保证为
`SECURITY_REVIEW_REQUIRED`。

**Verdict：`CONDITIONAL`**  
条件是 D2 仍存在可由合法最小 probe 区分的 residual；标准平台当前状态足够时删除该步骤。

### D4：一次协商是否需要物化 RelationVersion

**产品决定**  
决定产品何时只保留一次性请求/回复，何时建立可共同修改的 proposal/relation version，哪些
material change 必须重新取得双方决定，拒绝后哪些 descendants 归零。

**直接用户任务指标是否足够**  
一次性低风险请求中，双方原生 `request + response` 可能已经足够；仅以“最后达成一致”却无法
决定版本关系是否有增益。只有在 counter、多人异议、复用或漂移下，才需比较物化关系能否减少
误执行和重谈成本。

**已经发生的假绿**

- Wave006 G2 evaluator 完全不消费 relation evidence；删除证据结果不变，无证据低成本候选反而
  胜出。
- T4 candidate 在 Authority 未闭合时把 proposal 写成条件已满足，说明文本完整不等于承诺。
- Wave019 只有独立 owner response、显式接受 COUNTER、owner act、current-head revalidation 和
  removal/refusal descendants=0 后，才支持局部 formation。

**最小有区分力评测**

同一 PT-001 base task 做三个 paired branch：

1. one-shot request/response；
2. `COUNTER → 修改 → 双方确认`；
3. 确认后用途或时间发生 material change。

比较“只保留消息历史”与“显式 RelationVersion”是否在 owner-native decision、异议保留、错误
沿用、重谈轮数和下游阻断上产生差异。移除 relation evidence 后结果不应不变；若没有差异，
产品采用更简单的一次性状态。

**设施需求**

| 设施 | 当前需要 |
|---|---|
| 独立 evaluator | `YES`：从双方 decision source 与当前 head 判断，不读 controller summary |
| replay | `YES, CORE`：counter、material change、withdraw |
| 统计 | `NO`：paired removal 足以先判因果必要性 |
| byte determinism | `NO`：稳定 semantic ID/version/provenance 足够 |
| receipt gate | `YES` 对 owner decision；自动正式机制晋升为 `NO` |

**成本与停止点**  
一个 one-shot 与一个变更 episode 已足够决定是否引入 RelationVersion。只有物化版本在下游安全或
复用成本上产生可复现差异才保留；否则 `REMOVE`，不继续建设关系本体。

**Verdict：`CONDITIONAL`**  
协商、拒绝和 owner-native response 的证据是核心；独立 RelationVersion 设施只有在复用/变更中
显示材料增益时才必要。

### D5：能力声明何时可以成为可依赖承诺

**产品决定**  
决定 Agent Card、目录声明、历史记录、行为 probe、环境 readiness、资源预留与人工确认如何
组合；何时允许产品承诺，何时必须 abstain。

**直接用户任务指标是否足够**  
只看最终成功太晚，也无法区分稳定能力、运气、controller 代做或条件变化。若产品要在执行前
承诺，必须评价预测时刻的证据、expiry、当前环境和 holdout outcome；全部 Unknown 也不能以零
错误“获胜”。

**已经发生的假绿**

- Wave006 G4 以 strategy label 而不是实际 evidence access 收费；换函数不换标签即可作弊，
  7,200 点扫描继承了错误成本模型。
- T2 bounded probe 即使成功也只资格化一个冻结 synthetic operation，不建立业务 Effect 或
  未来可依赖性。
- Wave015 的组件接口全绿曾彼此不可组合；名称为 ledger 的内存字段也曾冒充 durable truth。

**最小有区分力评测**

在行动前冻结 `operation + executor + environment + version + permission + resource + expiry +
confidence`。再用小型 prospective holdout 注入一项权限变化、一项版本变化、一项资源冲突和一项
恢复。比较声明、声明+最近 probe、声明+readiness/reservation 与人工确认，测 false commit、
false reject、abstention、calibration 和恢复后同一 identity。

**设施需求**

| 设施 | 当前需要 |
|---|---|
| 独立 evaluator | `YES`：prediction 与 outcome truth 分离 |
| replay | `YES`：权限、版本、资源和恢复是承重条件 |
| 统计 | `CONDITIONAL, TARGETED`：校准需要多个 holdout，但按具体 operation family 扩样 |
| byte determinism | `NO`，除非跨 provider 收到相同冻结输入是比较前提 |
| receipt gate | `YES` 对 prediction/expiry/outcome binding；通用研究晋升门不需要 |

**成本与停止点**  
先用一个 operation family 的 8--20 个有意义扰动，而不是通用样本池。某证据组合达到预先声明的
false-commit 底线且不靠全 abstain 后进入产品；新环境/版本使误承诺复发时再重开。

**Verdict：`CORE_NECESSARY`**

### D6：同意、Authority、Commitment 与 Reservation 怎样分开建立

**产品决定**  
决定何时用平台原生授权，何时使用 policy/delegation adapter、人工 explain-back、签名 mandate
和 reservation；撤销在何处被消费才真正阻断执行。

**直接用户任务指标是否足够**  
绝对不够。未授权动作也可能产生用户想要的终态；认证、能力、同意、Authority 和执行成功不能
互推。必须从相应 Principal/Authority/Target 原生状态读取 allow/deny/currentness 和消费结果。

**已经发生的假绿**

- G5 曾存在 controller shortcut，真实 policy products 均 `NOT_RUN`。
- Wave006 G6/G7 持有全部测试私钥，可替 Authority 制造 L4 Acceptance。
- Wave018 初版相信 receipt 自报 `current=true`，没有查询 owner current head。
- Wave024 的 U 负控中远端 revoke 已存在，但 Target 未消费 matching fence，仍 raw commit；
  说明远端签名或 workflow 不能补出不存在的跨域顺序。
- Wave024 旧运行让 Authority 签 controller 提供的 receipt hash，却未自行验证 Target receipt
  语义，接受后被重开。

**最小有区分力评测**

对同一 resource operation 运行：允许、拒绝、过期、撤销已被 Target 消费、撤销尚未被 Target
消费、重复预留和 execution-time head 变化。独立 oracle 从 Principal/owner/Target 各自事实源
重算 scope、expiry、head、reservation 与 decision。U 类并发/无序必须保持 `NOT_SCORED`，不能
为了漂亮结果算成功或失败。

**设施需求**

| 设施 | 当前需要 |
|---|---|
| 独立 evaluator | `YES, CORE` |
| replay | `YES, CORE`：撤销、过期、TOCTOU、重复预留 |
| 统计 | `NO`：结构性反例不需大样本 |
| byte determinism | `CONDITIONAL`：签名/版本 transition 的 canonical bytes 需要精确绑定 |
| receipt gate | `YES AS PRODUCT AUTHORITY GATE`；自动研究主张 promotion 仍为 `CONDITIONAL` |

**成本与停止点**  
完成上述六个状态及一个平台原生正控后，足以选择平台、adapter 或人工 gate。不得在本审查中
实施权限攻击或声称不可绕过；密钥隔离、同 UID/目录攻击、网络和主机信任均为
`SECURITY_REVIEW_REQUIRED`。

**Verdict：`CORE_NECESSARY`**

### D7：由平台直达、合法强中心还是跨主体组合执行

**产品决定**  
按 Authority stratum 和任务结构选择最简单可靠执行路径；稳定平台任务必须旁路开放 formation，
跨独立 Authority 时不能让中心代 owner 行动。

**直接用户任务指标是否足够**  
在 `U / LAWFULLY_UNIFIED` 平台内，平台 authoritative terminal state 加用户 Acceptance 可以足够；
在 `P / PLURAL_INDEPENDENT` 中，“终态满足”不能证明由候选 arm、合法 actor 或当前授权产生，
还需要 Target-native actor/readback 和 owner decisions。

**已经发生的假绿**

- Wave014 双生世界由 A4 与 Helper 产生完全相同终态；legacy evaluator 两者都判 A4 成功。
- Wave017 反向证明平台原生能力在合法统一域用一次 native call 完整解决 E0；若仍强加 relation
  或 federation，就是产品复杂度错误。
- Wave021 只冻结公平合同，actual comparison=`0`、winner=`NONE`；不能从合同推断任一 arm 胜出。
- Wave023 static validator 曾接受五类 runtime 假绿，开发 manifest 不能改名为实际运行。

**最小有区分力评测**

先做 applicability routing，不做全局冠军赛：

- U：现有平台直达作为默认正控；
- D：精确 delegation 下比较平台/中心 adapter；
- P：只比较保留 owner-native decision 的组合，lawful center 可为 `NOT_APPLICABLE`。

每层只运行一个具体 PT-001 episode，使用同一 Q、public view、owner/Target API 和结果向量；如果
平台原生已经完整解决，立即 `ADOPT` 并停止比较。只有两个可行路径在用户结果/成本上无法决定时，
才增加 targeted blind holdout。

**设施需求**

| 设施 | 当前需要 |
|---|---|
| 独立 evaluator | `YES` 对 P/D；U 可直接采用平台权威状态加外部 Acceptance |
| replay | `CONDITIONAL`：ACK-lost、撤销或恢复会改变执行路径时需要 |
| 统计 | `NOT_YET`：先以 applicability 和结构性底线淘汰 |
| byte determinism | `CONDITIONAL`：只有跨 arm 公平输入需要 |
| receipt gate | `YES` 对 Target completion；通用 sealed-run admission 不需要 |

**成本与停止点**  
每个 Authority stratum 选出一个满足底线的最简单路径即停止。当前没有产品决定需要 A1--A5 的
通用全臂大样本排名；Wave025 full qualification 不应成为 D7 前置条件。任何运行隔离或防泄漏
安全保证为 `SECURITY_REVIEW_REQUIRED`。

**Verdict：`CORE_NECESSARY`**  
必要的是 applicability + 同任务最小比较，不是通用比较基础设施。

### D8：何时产品可以显示“已完成”

**产品决定**  
定义 ActionAttempt、Target Effect、Adoption、各方 Acceptance 和 Settlement 的产品状态；哪些
证据缺失时只能显示 pending/unknown/disputed。

**直接用户任务指标是否足够**  
若“直接指标”指 Target authoritative readback 与有权主体的真实 Acceptance，它们就是核心证据；
若只是 controller、agent 或 UI 报告“完成”，绝对不够。任务终态相同还不能证明 actor/Authority，
已有状态也不能冒充本次 Effect。

**已经发生的假绿**

- Wave013 第一 actual bundle 得到 `UNSAFE_EFFECT / INVALID_REFUSAL`；删除 execute request、错误
  deadline 或存在替代方案时仍可能绿。
- Wave014 证明相同 Target state 不足以归因。
- Wave019 在早期粗粒度 occurrence 之后补足 46 sample、Target、其他线路、功率、安全、噪声、
  时长和 deadline 的逐项绑定，说明“有一个 occurrence”不足。
- Wave020 removal 中 source 已执行相同 occurrence，但 migrated 看不到 durable Target evidence，
  正确结果是 `BOUNDED_UNKNOWN`、零 Acceptance/finality，而不是补写成功。

**最小有区分力评测**

对 PT-001 冻结一个极小、可撤销真实动作和权威 readback。至少包括：

- pre-existing state；
- authorized actor effect；
- helper/other actor matching state；
- Attempt 发生但 Effect 未发生；
- Effect 发生但一方拒绝 Acceptance；
- duplicate/retry。

独立 evaluator 从 Target 与 Acceptance owner 原生来源重算。产品 completion gate 只在 exact
operation readback 与所需 Acceptance 都存在时晋升；有争议时保留分层状态，不把最终平均分
盖过底线。

**设施需求**

| 设施 | 当前需要 |
|---|---|
| 独立 evaluator | `YES, CORE` |
| replay | `YES`：pre-existing、other actor、duplicate/ACK-lost |
| 统计 | `NO`：结构性真假例足够建立状态机 |
| byte determinism | `CONDITIONAL`：只对 receipt/readback exact binding |
| receipt gate | `YES, CORE`：这是产品 completion gate；不等于研究 claim 自动 promotion |

**成本与停止点**  
上述六个真假分支可稳定区分后停止扩建 evaluator，接入真实任务。新增领域只需换 Target adapter/
witness，不重造通用 truth 系统。物理、法律或安全 witness 的充分性由相应专业人员审查，本研究
只标 `SECURITY_REVIEW_REQUIRED` 或领域复核需求。

**Verdict：`CORE_NECESSARY`**

### D9：拒绝、撤销、ACK 丢失、失败或漂移后重开什么

**产品决定**  
决定何时 retry、reconcile、找替代方、局部重谈、全局重开或退出；禁止重复 Effect 和把临时
不可用误判为规范关系失效。

**直接用户任务指标是否足够**  
“最终恢复了”不够：可能已经产生第二 Effect、沿用撤销授权、全局重开制造无谓成本，或在没有
readback 时假装成功。需要从同一 base episode 的真实依赖和原生状态判断受影响闭包。

**已经发生的假绿**

- Wave016 区分 ACK 丢失后的已提交与未提交；只有 exact signed status/readback + freshness 才能
  决定 reconcile 或 safe retry。
- Wave018 初版内存 ledger、旧 current receipt 和 WAL 主文件均制造假闭包；最终才支持 revoke、
  rediscovery 与 bounded refusal。
- Wave020 曾出现 worker 参数漂移、旧 artifact、错误 object、假 restart、移除投影仍能读 full
  capsule、pre-crash absence 自报与反事实标签泄漏。
- Wave024 U 证明远端 revoke 与 Target fence 无序时必须 Unknown/Not scored，不能强行选边。

**最小有区分力评测**

从 D8 的真实 base episode 生成五个 product replay：

1. ACK 丢失但 Effect 已发生；
2. ACK 丢失且 Effect 未发生；
3. 对方 `REFUSE/COUNTER/REVOKE`；
4. capability/permission/goal 中只变化一项；
5. 原伙伴失效但存在替代方。

评价 duplicate Effect、unsafe continuation、漏/多重开、恢复时间、保留的无关承诺和最终
Acceptance。replay 必须引用同一 base run 和真实 dependency，而不是单独写新结果 JSON。

**设施需求**

| 设施 | 当前需要 |
|---|---|
| 独立 evaluator | `YES, CORE` |
| replay | `YES, CORE` |
| 统计 | `CONDITIONAL`：先覆盖 failure class；频率与 SLA 再用现实数据 |
| byte determinism | `NO`，除 exact receipt/status binding |
| receipt gate | `YES` 对 retry/reopen/complete transition；自动删除历史证据为 `NO` |

**成本与停止点**  
五类 replay 能区分正确动作且零 duplicate Effect 后，先接入产品。更多同质 mutation 交给回归；
只有新 failure class 改变依赖闭包时扩展。不可预告硬崩溃、跨机非干扰、同权限恶意 writer 等
安全/基础设施保证不在本审查实施，标 `SECURITY_REVIEW_REQUIRED`。

**Verdict：`CORE_NECESSARY`**

### D10：形成的路径是否值得编译、复用和长期维护

**产品决定**  
决定一次成功是继续开放协商、编译为平台/中心路径、保留轻量 adapter，还是因维护与治理成本
退出。

**直接用户任务指标是否足够**  
初次完成率、用户 Acceptance 和总历时足以做早期 go/no-go；但不能决定“编译后是否降低全生命
周期成本”。还需第二次运行、一次漂移、人工判断、披露、等待、恢复、维护和迁移成本。token
不是主要成本。

**已经发生的假绿**

- Wave006 G4 的 label-based cost 让换函数不换标签即可作弊；7,200 点扫描不能修复输入错误。
- Wave021 只有成本向量与公平合同，没有 A1--A5 actual run，不能宣称成本赢家。
- Wave022 明确现实人力可能在系统外填补语义缝；当前没有真实数据证明组合降低了 material
  judgment，还是转移到接入和治理。

**最小有区分力评测**

只有 D0 得到真实任务且 D8 首次真实完成后，才记录：

- 第一次形成的总历时、询问、披露、人工判断、错误和返工；
- 同条件第二次运行；
- 一次局部漂移后的恢复；
- 对照现有平台/人工流程；
- adapter/依赖的维护、停更、替换和迁移负担。

先用原始可读计量，不急于统一货币化。

**设施需求**

| 设施 | 当前需要 |
|---|---|
| 独立 evaluator | `CONDITIONAL`：任务结果仍由 D8；成本 ledger 可由独立审计抽样 |
| replay | `YES AFTER BASE RUN` |
| 统计 | `CONDITIONAL`：多个真实 episode 后才估计分布 |
| byte determinism | `NO` |
| receipt gate | `CONDITIONAL`：外部 provider/人工计量需要来源凭据，但不需自动 promotion |

**成本与停止点**  
当前连一个现实 PT-001 base episode 都没有，因此不建设通用经济 evaluator。完成“首次、第二次、
一次漂移和一个可比基线”后即可作首个 compile/keep-open 决定；只有决定对规模投入敏感时才
扩样。

**Verdict：`CONDITIONAL`**

## 四、跨决定设施总表

| 设施 | 当前总 verdict | 直接服务的产品决定 | 最小充分形态 | 明确停止点 |
|---|---|---|---|---|
| 真实任务 specimen + member-check | `CORE_NECESSARY` | D0--D10 的共同分母 | 一个独立于 R7 的具体低风险任务、各方 S0/Q/拒绝/Effect/Acceptance | 一个可认领 task v1；随后进入真实 episode，不扩成任务库 |
| fresh truth/solver separation | `CORE_NECESSARY` | D1--D3、D5、D7 | 一个未见 holdout task/变体，oracle 不进 solver 输入 | 已能揭露 answer leakage/post-oracle 修补 |
| 独立 Effect/readback/Acceptance evaluator | `CORE_NECESSARY` | D7--D9 | 直接读取 owner/Target 原生来源，不 import solver | 六个关键真假分支稳定区分 |
| disclosure/询问/漏机会/误唤醒计量 | `CORE_NECESSARY` | D1--D3 | recipient/purpose/retention/refusal + recall/false wakeup/rounds | 选出默认前沿后停止；新任务分布漂移才重开 |
| owner-native Authority/decision evidence | `CORE_NECESSARY` | D3--D8 | scope/version/expiry/head/decision/reservation/consumption | allow/deny/stale/revoke/U/duplicate 均可区分 |
| base-episode failure replay | `CORE_NECESSARY` | D4--D10 | ACK-lost、counter/refuse/revoke、单项 drift、alternative | failure classes 已覆盖且零重复 Effect，转回归 |
| 产品 completion/reopen gate | `CORE_NECESSARY` | D8--D9 | 缺 exact readback/required Acceptance 不得 completed；Unknown 保留 | 状态机真假例通过后不扩成研究晋升系统 |
| targeted prospective statistics | `CONDITIONAL` | D2、D5、D10 | 仅围绕具体 recall/calibration/cost 决定扩样 | 置信区间已跨过预注册产品底线或仍重叠则 KEEP_UNKNOWN |
| authority-stratum 最小机制比较 | `CORE_NECESSARY` | D7 | U/D/P 内同一任务比较最简单可行路径 | 找到满足底线的简单方案即停止 |
| full A1--A5/C1--C3 blind tournament | `NOT_JUSTIFIED_YET` | 尚无具体产品决定只能靠它判断 | 无 | 出现同 stratum、同任务、近似同分且高代价的真实候选前不启动 |
| 通用 3,200 blind population | `NOT_JUSTIFIED_YET` | 尚无 | 无 | 只有 targeted 小评测功效不足且错误选择代价更高时才重新论证 N |
| C01--C05 通用 feature/classifier | `NOT_JUSTIFIED_YET` | 尚未绑定产品机制 | 无；D1--D3 先用 fresh holdout 和注册攻击 | 只有自动泄漏分类会改变某个产品机制选择时恢复 |
| MODEL-INPUT 通用资格 | `NOT_JUSTIFIED_YET` | 尚无真实 provider/model 产品决策 | 无 | 具体 provider treatment 进入 D7 且输入泄漏无法用小评测排除时恢复 |
| byte-level deterministic math | `CONDITIONAL` | D2/D3/D6/D8 的 exact input/signature/evidence binding | 局部 canonical bytes + hash；不建通用数学子系统 | 相同输入和证据可跨实现重算即停止 |
| 原生 event/decision/Target receipts | `CORE_NECESSARY` | D3、D6、D8、D9 | 事实 owner 在事件处签/记，绑定 exact scope/version/actor/readback | 足以支持产品状态转换即停止 |
| 自动 research receipt promotion/deletion gate | `NOT_JUSTIFIED_YET` | 当前产品不自动改变正式研究机制状态 | 无 | 只有产品本身需要无人值守改变正式状态且人工 gate 成为真实瓶颈时重开 |
| OCI/VM/主机/权限/网络隔离 qualification | `SECURITY_REVIEW_REQUIRED` | 可能影响未来 blind comparison 或部署安全 | 本审查不定义、不实施 | 交安全人员；不得由本研究给出安全结论 |

## 五、为什么原生证据核心必要，而 Wave025 full stack 仍不必要

Wave013--024 的共同教训不是“凡事都要 3,200 样本和复杂 classifier”，而是不同错误需要不同
最小判别器：

| 已发生错误 | 最小能阻止它的设施 | 不需要先建设的设施 |
|---|---|---|
| case label/hash/argv 泄漏 | fresh holdout + solver/oracle 分离 +实际 visible transcript | 通用五 classifier 大赛 |
| controller 代 owner 签字/写完成 | owner-native decision/readback + 独立 evaluator | 大样本统计 |
| 相同终态由 Helper 造成 | Target-native actor receipt/readback + one causal twin | 3,200 clones |
| ACK 丢失后误重试 | exact Target status/readback + paired committed/not-committed replay | 通用 feature system |
| stale `current=true`/撤销未消费 | owner current head + Target-consumed fence + U=`NOT_SCORED` | 单一总分或全局冠军赛 |
| occurrence 粗粒度假 Effect | exact task coordinates + Target/Acceptance binding | byte-level 数学包装 |
| 组件各绿但不可组合 | 同一 episode schema/truth owner 的端到端运行 | 测试数量相加 |
| WAL 主文件/旧 artifact/接口漂移 | 所选事实存储的原生完整性和独立 readback | 所有产品事件都进入 formal artifact gate |
| static manifest 冒充 actual run | 真实 candidate/owner/Target presence receipt | 继续美化 manifest |
| fixed S→R→U 顺序破坏 blind claim | 对需要比较的具体任务做 fresh random holdout；安全隔离另审 | 在产品主链前完成 Wave025 全部 qualification |

因此，独立 evaluator、readback、Acceptance、failure replay 和任务真实性是产品链的承重设施；
Wave025 的 full profile 只是一种可能的未来方法，不是这些真实性要求的唯一实现。

## 六、设施投资顺序

### 现在做

1. 找到/构造并 member-check 一个独立于 R7 清单的具体 PT-001 用户任务；
2. 为它分离 `FUZZY-INPUT`、owner-private truth、Target/readback 和 Acceptance source；
3. 先画用户动作与产品状态，不先建统一 evaluator 平台；
4. 运行 D1/D2 的小型 fresh holdout，决定澄清、目录、投影和 probe 路由；
5. 只对入选路径接 owner-native Authority、Target Effect 与 Acceptance gate；
6. 从同一 base episode 运行拒绝/撤销/ACK-lost/单项 drift replay。

### 出现条件后做

- 两个具体机制在同一真实任务上都满足底线、直接用户结果近似同分，且错误选择代价高：增加
  targeted statistics 或 blind comparison；
- 产品要自动承诺能力：增加 prospective holdout/calibration；
- 跨 provider 精确输入或签名证据无法复算：增加局部 byte determinism；
- 产品要无人值守改变正式状态：评估自动 receipt promotion gate；
- 部署或比较需要安全隔离保证：交 `SECURITY_REVIEW_REQUIRED`。

### 当前不做

- 无产品决定绑定的 3,200-slot formal batch；
- 通用 C01--C05、MODEL-INPUT 和 classifier qualification；
- 为形式完整而统一所有 feature/evaluator schema；
- 自动删除失败证据或从 receipt 晋升正式机制主张；
- 任何网络、容器、主机、权限攻击或安全结论。

## 七、最终判定规则

一项新评测设施只有同时满足以下条件才进入建设：

```text
存在 named PT-001 product decision
AND 已有真实或可认领 task prestate
AND 直接用户/Target/owner 指标不能区分竞争机制
AND 已发生或高代价的假绿能由该设施阻止
AND 没有更小的 paired/holdout/readback 评测可作决定
AND 预先写明 ADOPT/COMPOSE/REMOVE/INVENT/KEEP_UNKNOWN 的触发结果
AND 预先写明决定完成后的停止点
```

任何一项不成立，设施保持 `CONDITIONAL` 或 `NOT_JUSTIFIED_YET`。这不是降低严谨性，而是把
严谨性集中在真正承重的产品事实上：用户目标有没有被保留、对方有没有真实同意、行动有没有
发生、由谁发生、谁接受、以及失败时是否安全恢复。
