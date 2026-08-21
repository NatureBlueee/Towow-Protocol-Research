# PT-001 产品链与评测设施必要性综合

状态：`INTEGRATED_THREE_PARALLEL_RETURNS / PRODUCT_DECISION_REBASE`

> 目录名 `product-chain-t1-t3` 是本轮真值校正前建立的工作名，不代表 T3 已提供现实任务证据。
> 当前正典锚点是新建的 `PT-001-FUZZY-RESOURCE-COLLABORATION`，证据级别为
> `NEW_SYNTHETIC_PRODUCT_TASK_CANDIDATE`。

## 一、这轮要作出的不是“要不要评测”

真正要作出的判断是：

> 为了决定通爻产品采用什么机制、怎样组合、哪里需要完整创新，我们分别需要什么证据；哪些
> 证据必须由专门设施产生，哪些可以直接由任务结果得到，哪些设施当前还没有建设理由。

因此不采用“基础设施都停掉”或“先把通用实验室补完”这两个极端。必要设施要按其承担的
产品决定完整建设；但设施不能脱离决定而自我扩张。

“完整”是相对于它要支持的主张，不是相对于一个无限通用平台。至少需要：

- 冻结待决定的产品行为和竞争方案；
- 有与该行为对应的任务前态、合格结果和失败分支；
- 让方法只能看到产品实际可见的信息；
- 结果来自相应 truth owner，而不是 controller 或候选方法自报；
- 能揭露已经发生过的假成功；
- 预先说明什么结果会导致采用、组合、删除、创新或保持 Unknown；
- 作出决定后有停止点。

本综合保留三份并行返回的不同粒度，而不强行制造一种统一形式：

- [`01-user-journey-reconstruction.md`](./01-user-journey-reconstruction.md) 用 12 个用户节点检查每一步
  的可理解性、拒绝、Unknown、失败回点和价值；
- [`02-mechanism-composition-map.md`](./02-mechanism-composition-map.md) 用 N0--N12 检查现有机制、
  强中心、通用模型、人工制度与 adapter 的条件化组合；
- [`03-evaluation-necessity-map.md`](./03-evaluation-necessity-map.md) 用 D0--D10 独立判断每个产品
  决定需要什么证据、设施成本和停止点。

编号不同不是冲突：用户节点、机制节点和评价决定本来就不是同一种对象。它们在同一产品链上
通过具体决策对齐。

## 二、PT-001：先把产品问题变成一条用户能够经历的链

当前采用一个合成但现实可识别的资源协作任务作为设计探针：

> 一个设计团队只知道自己需要在截止日前得到符合若干隐含要求的实体原型，但不知道需要什么
> 设备、操作人员和场地。某 makerspace 可能提供激光切割时段，但资源所有者、操作技术员、
> 安全批准者、付款者和最终验收者可能不是同一主体；各方可以少披露、拒绝、反提案或撤销。

这不是现实完成案例，不产生 90% 或 95% 覆盖率。它的作用是迫使产品设计同时面对：模糊目标、
未声明能力、条件创造、局部信息、拒绝、权威分散、真实执行和独立验收。

### 用户可见旅程

| 阶段 | 用户看到和能够做什么 | 系统必须保持的真实区别 | 阶段成功不代表什么 |
|---|---|---|---|
| 1. 表达目标 | 用自然语言说明“想得到什么”，可以暂时不知道资源名和执行方法 | 原始价值、截止时间、不可接受底线、Unknown | 不代表 query、任务规格或资源已形成 |
| 2. 暴露缺失条件 | 系统指出哪些条件会改变可行性，只询问当前最承重的问题；用户可确认、改写或拒答 | 已知、推断候选、必须询问、允许未知、拒绝披露 | 不代表拒答即无机会，也不代表模型推断是真实偏好 |
| 3. 选择披露与探索范围 | 用户看到每次探索要向谁披露什么、为什么、保留多久，并可缩小范围 | 本地上下文、最小投影、接收者、目的、版本、累计披露 | 不代表允许披露就是允许合作或执行 |
| 4. 获得可修改的可能性 | 若现成平台可直达就直接给出；否则呈现资源、伙伴、改变条件或培养能力的候选路径 | 已表达搜索结果、未表达但经 reciprocal probe 形成的候选、条件创造、目标重写 | 不代表被找到就是有能力、愿意合作或已经形成关系 |
| 5. 双方澄清与反提案 | 请求方与资源方可分别补充、拒绝、缩窄或 counter；系统保留未决项 | 各方自己的立场、关系版本、同意范围、未决冲突 | 不代表聊天达成一致，也不代表关系蕴含当前许可 |
| 6. 资格化与承诺 | 用户看到能力证据、试做或有界 probe、预约、费用、撤销和失败责任，再分别确认 | Capability prediction、Mandate、Commitment、Reservation、Standing | 不代表历史成功保证本次能力，也不代表 policy Allow 等于承诺 |
| 7. 执行 | 在执行前再次核对当前版本、权限和资源；执行一个精确、有界动作 | exact operation、attempt-time authority、idempotency、target state | 不代表 workflow completed 就产生了目标 Effect |
| 8. 验证结果 | 系统读取目标域结果；有权验收的人可以接受、拒收或要求修正 | Attempt、Effect、Adoption、Acceptance、Settlement | 这些状态互不自动推出 |
| 9. 局部重开 | 权限撤销、资源失效、目标变化或拒收时，只重开受影响部分；可换伙伴、改条件或终止 | 依赖、历史事实、当前有效性、补偿、替代路径 | 不代表全停或全重做就是安全恢复 |

该旅程的产品价值不是“让用户管理协议对象”，而是让用户在不必一开始知道全部条件和技术名词的
情况下，仍能看懂当前缺什么、为什么需要披露、谁尚未同意、哪一步真的发生了、失败后还能怎样
继续。

## 三、逐产品决定选择机制，而不是先选技术名

| 产品决定 | 当前最强候选组合 | 当前判断 | 必须区分的失败 | 最小充分评测 |
|---|---|---|---|---|
| D1 何时直接完成，何时进入开放形成 | 平台原生能力/强中心 direct + 任务边界识别 + 明确 no-match | `COMPOSE_CANDIDATE` | 为简单任务强行协商；把平台 no-match 当世界无解 | direct 负控与开放任务成对运行，测多余步骤、完成率和误旁路 |
| D2 怎样从模糊目标形成下一问题 | 通用模型或人类访谈 + 本地上下文 + 目标/底线确认 + typed Unknown | `COMPOSE_CANDIDATE` | 目标替换、穷举问卷、臆测偏好、只会检索已形成 query | 隔离的模糊输入和隐藏必要条件，测任务推进、问题数、误推断和目标保持 |
| D3 怎样控制披露仍能创造可能性 | 本地 policy + task-relative projection + 渐进披露 + 用户可拒绝 + receipt | `COMPOSE_CANDIDATE` | 零披露却声称完整发现；单轮合规但累计泄露；拒绝被解释为无能力 | disclosure/possibility frontier，记录累计披露、漏机会、误唤醒和合法不可发现 |
| D4 怎样找到或生成合作可能性 | 已表达切片用 ARD/目录/A2A Card；未表达切片用 local trigger + routing + reciprocal probe；强中心在合法全量输入时作为正基线 | `COMPOSE_CANDIDATE` | 把索引当 query genesis；单边可能性当互补完成；陈旧 card 继续生效 | expressed/unexpressed、current/stale、match/no-match paired worlds；测 qualified opportunity 和 false wake |
| D5 怎样判断能力可依赖或需要培养 | 历史证据 + 当前环境检查 + 有界试做/holdout + 工具/训练/人类补足 + abstain | `COMPOSE_CANDIDATE` | 历史成功回填本次能力；全 Unknown 伪安全；把训练建议当能力已形成 | 前瞻 holdout 和环境变化，测 false commit、false reject、校准、恢复与培养后的真实变化 |
| D6 怎样形成关系、授权和承诺 | 人类工作流/HITL + IAM/policy + scoped delegation + reservation；一次请求可保留简单状态，只有 material change/复用时才物化 RelationVersion | `AUTHORITY_CORE / RELATION_VERSION_CONDITIONAL` | durable relation=当前允许；policy Allow=Commitment；旧版本授权穿透撤销 | relation/authority crossed square，含 one-shot、counter、refuse、revoke、reservation 冲突和 attempt-time recheck；删除 RelationVersion 后若无差异就采用简单状态 |
| D7 怎样执行真实动作 | 平台原生执行优先；否则 workflow/A2A/MCP adapter + idempotency + target-native operation ledger/readback | `ADOPT_OR_COMPOSE_BY_TASK` | controller 代做、workflow 自报、重复副作用、错误对象成功 | 精确操作的 target readback、并发/重试/预存在状态 mutation；不要求先建通用比较平台 |
| D8 怎样确认完成和被接受 | target authority 的 Effect readback + 独立 beneficiary/acceptance authority 的显式决定 | `CORE_PRODUCT_BOUNDARY` | Effect、Adoption、Acceptance、Settlement 相互冒充 | 独立 truth owner、错误对象/他者造成相同状态 causal twin、拒收与部分采用 |
| D9 怎样在变化后继续 | 版本化依赖 + invalidation + scoped reopen + compensation + rediscovery | `COMPOSE_CANDIDATE` | 全停、全重开、继续使用失效事实、改写历史 Acceptance | 在合格 base task 上注入撤销/失效/拒收，测漏重开、误重开、unsafe continuation、恢复成本 |

以上都是候选产品决定，不是已经证明的完整方案。若成熟组合在同分母任务上完整解决，它就直接
成为通爻方案；只有留下稳定、可观察残余的位置才进入 `INVENT`。

三条返回目前没有支持任何 `INVENT` 晋升。最接近真实残余的两个位置是“未表达机会怎样在合法
披露下进入候选”和“变化后是否值得自动局部重开”；它们都保持 `KEEP_UNKNOWN`，先由成熟组合、
人工 fallback 与任务证据检验。

## 四、评测设施的必要性分层

### A. 当前核心必要：没有它就无法判断产品是否解决问题

| 设施能力 | 为什么直接必要 | 最小可用形态 | 建成后的停止点 |
|---|---|---|---|
| 完整任务前态与合格结果 | PT-001 当前仍是合成任务，R7 资源清单不能冒充真实输入 | 至少一个独立来源的完整任务 S0、原始价值、权威、拒绝和 Q；在此之前只做产品假设 | 能运行一条完整链并逐项标 PASS/PARTIAL/FAIL/UNKNOWN |
| 独立 Effect/readback/Acceptance | 没有它会把输出、workflow green 或 controller 自报当完成 | 目标域权威 readback + 有权验收主体的独立接受/拒绝 | 能稳定揭露错误对象、他者造成结果、Effect 无 Acceptance 等假绿 |
| query genesis 与缺失条件评测 | 产品承重处正是用户还不知道该搜什么 | 模糊输入、隐藏但任务承重的条件、允许 Unknown/拒答的 evaluator | 能区分访谈、推断、直接平台和组合对任务推进的真实贡献 |
| 披露—可能性前沿 | 完整发现与有限披露之间的张力不能靠结果成功率单独解释 | 累计披露、recipient/purpose/version、qualified opportunity、miss/false wake 联合记录 | 能决定中心化、本地投影、渐进披露和停止策略 |
| 拒绝、撤销与局部恢复 | 可拒绝、可撤销和重开是产品链的一部分，不是异常附录 | 合格 base-run + refuse/revoke/change mutations + affected truth | 能判断继续、局部重开、换伙伴、补偿和终止哪种行为正确 |
| 假绿回归集 | controller 代做、答案泄漏和 evaluator 错误已经真实发生并改变过结论 | 每种已发生假绿一个最小反例，随相关机制评测运行 | 已知假绿不能再次晋升产品决定 |

这些设施应当建设，而且要做到足以支撑相应产品决定。它们不是面向用户的功能，却是产品研究
不可缺少的测量能力。

其中可以复用 Wave025 已有的 runner、holdout、evidence 或 readback 部件，但复用后它们只服务
当前命名的产品决定；不能因为复用了代码，就把 Wave025 原来的通用 3,200 目标一并恢复。

### B. 条件必要：有明确产品选择且较小评测无法区分时完整恢复

| Wave025/相邻设施 | 恢复触发 | 当前为什么不主动补齐 |
|---|---|---|
| 通用 3,200 样本 blind comparison | 某个高影响产品机制在小型真实任务、反例和异质迁移后仍无法区分，并需要统计把握 | 当前没有一个已命名的产品决定需要 3,200；任务真值本身仍缺 |
| 通用 feature、C01--C05、classifier、MODEL-INPUT | 产品确实要自动识别会污染比较或泄漏答案的输入，而且人工/结构隔离不足 | 它们目前主要服务通用实验准入，不是 PT-001 的产品机制 |
| byte-level deterministic math 与跨 provider 精确复现 | provider 差异可能改变一个产品决定，且语义级任务结果无法定位差异 | 当前决定集中在产品链和 truth owner，尚无此残余 |
| 通用 evaluator engine 与 batch adapter | 至少多个已命名产品决定复用相同评价语义，手工任务 evaluator 开始造成不一致 | 先抽象会把尚未稳定的任务差异压平 |
| 自动 receipt promotion/deletion gate | 系统被授权自动改变正式研究或产品状态，错误晋升代价高 | 当前正式机制决定仍需用户/外部权威，不需要自动删除或晋升 |
| 大规模 seal/隔离与攻击设施 | 非安全研究所需的答案隔离、只读 worker 等有明确证据需求时只做已允许的部分；网络/权限攻击另交安全人员 | 用户已要求网络安全敏感部分只标记、不继续，本研究不作安全保证 |

`CONDITIONAL` 的含义是：一旦触发，就按决定所需范围做完整；未触发时不以“以后也许有用”为由
继续建设。

### C. 当前无充分理由

- 为完成 Wave 编号而把所有候选设施补齐；
- 与产品决定无关的 classifier 排名或 C01--C05 胜负；
- 在没有真实任务分母时先追求漂亮 coverage 百分比；
- 把文件数、测试数、哈希数、样本数或多模型共识作为产品接近解决的代理；
- 用同一模型、同一真值生成器和同一 evaluator 的大量重复替代异质任务证据。

## 五、设施升级规则

评测从最低成本、最接近任务的证据开始，只在前一级不能回答产品决定时升级：

1. **L0 任务结果**：真实执行、目标域 readback、主体 Acceptance 和成本。
2. **L1 任务专用 evaluator**：把隐藏条件、拒绝、反例和错误对象冻结，防止自证。
3. **L2 比较任务集**：当一个案例可能是偶然，加入异质任务、留出变体和组件消融。
4. **L3 可复用设施**：多个已命名产品决定共享稳定语义后，抽象 runner、evaluator 和证据对象。
5. **L4 统计规模**：只有剩余差异需要频率或置信度判断时，扩到相应样本量；样本量由待区分效应
   和错误代价决定，不由预设数字决定。

每次升级都要回答：低一级具体无法区分什么；新设施会改变哪个产品决定；错误决定的代价是否
高于建设和维护成本；什么结果出现后停止。

## 六、七条母线怎样共同服务同一产品链

| 母线 | 在 PT-001 中负责的产品问题 | 不得冒充的其他事实 |
|---|---|---|
| G1 发现与边界 | 模糊目标、query genesis、合法可发现性、qualified handoff | 搜索结果不等于关系、能力或同意 |
| G2 问题与关系构成 | 多方提案、版本、materiality、counter 后共同关系语义 | durable relation 不等于当前许可 |
| G3 可能性形成 | 找到已有路径、创造新条件、培养能力或重写问题，并区分不可达 | hindsight path 不等于事前可形成 |
| G4 能力兑现 | 对精确 attempt 的前瞻可依赖性、abstain 和恢复 | 事后成功不回填事前能力判断 |
| G5 权威与规范 | Principal、授权、承诺、预约、撤销和 attempt-time gate | controller、账号或 role label 不等于 Authority |
| G6 现实效力 | Attempt、Effect、Adoption、Acceptance、Settlement 的独立 truth | workflow completed 不等于目标完成 |
| G7 运行与演化 | 变化后的 affected closure、局部重开、恢复和复用净值 | 全停或全重做不等于正确恢复 |

七条线可以保留各自 evaluator 和反例，但不能各自把同一产品旅程重造为七套系统。跨线综合的
输出是 D1--D9 的产品机制决定，以及它们之间的 truth/authority handoff。

## 七、下一步与当前证据边界

1. 先补一份独立于 R7 资源清单的 PT-001 完整任务前态；若只能先做合成实例，继续明确标记。
2. 用一个最小产品原型走通 D1--D9，但不先暴露协议对象给用户。
3. 第一轮只建设上述核心必要设施，先比较 direct platform、lawful strong center、通用模型+
   成熟组合、人类制度/工作流与组合 adapter。
4. 每个节点输出 `ADOPT / COMPOSE / REMOVE / INVENT / KEEP_UNKNOWN` 及适用条件。
5. 只有某个产品决定在这些证据下仍无法区分，才为它恢复 Wave025 对应设施；不恢复整套 Wave025。
6. 网络安全、隔离绕过和真实攻击继续保持 `SECURITY_REVIEW_REQUIRED / DEFERRED_TO_SECURITY_PERSONNEL`。

当前能支持的结论是：评测设施中已有明确的核心必要部分，也有尚未证明必要的通用扩建部分；
我们已经有能力按产品决定把两者区分开。当前不能支持 PT-001 已解决、成熟组合已完整覆盖、任何
百分比覆盖率、现实主体已接受或系统具备安全保证。
