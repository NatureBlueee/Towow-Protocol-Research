# Wave 021–025 与 PT-001 研究沉淀

日期：2026-08-01  
沉淀状态：`HISTORICAL_RESULTS_PRESERVED / PRODUCT_MEANING_REBASED / NO_NEW_RUN`  
作用域：只整理 Wave 021–025 与 PT-001 的启动原因、实际结果、假绿与漂移、保留项、未运行项、产品意义和继续条件；不为任何机制补写新证据。

## 1. 总结判断

这五轮工作的真实演进是：先试图为 A1–A5 建立公平比较，随后发现静态准入会放过运行时假绿，于是不断加固 sealed admission、Authority/Target 因果边界与 blindness 资格。过程中确实得到一项可复用的下游能力结果（Wave 024），也暴露了多类会污染比较的具体反例；但 Wave 021、023、025 的主要产物是研究准入和反例，不是产品解决结果。Wave 022 是结构性综合，不是实验。A1–A5/C1–C3 从未完成实际横向比较，赢家始终不存在。

PT-001 则是在意识到研究设施与产品决定脱节后，为 D1/D2 准备的合成入口探针。它只用于判断怎样从模糊输入形成一个忠实、可拒绝、保留 Unknown 的 episode 入口，以及怎样给出下一步候选；它没有运行，也没有形成 RelationEpisode，更没有执行、Effect 或 Acceptance 结果。把 PT-001 D1/D2 扩张为新的独立主线，会重复此前的漂移。

当前统一处置如下：

| 对象 | 已取得的最高结果 | 当前处置 |
|---|---|---|
| Wave 021 | 公平取向与静态合同冻结；比较运行数为 0 | 保留为比较纪律；暂停，按命名产品决定调用 |
| Wave 022 | 六类端到端闭合缺口与局部软件结果的结构性综合 | 保留为解释图；不作为独立证据继续扩展 |
| Wave 023 | 开发 manifest smoke 可接受；任何实际比较准入均被拒绝 | 保留假绿回归；暂停通用 sealed-run 扩建 |
| Wave 024 | 三项本地合成下游能力获有界支持；blindness 失败；更强 currentness 未检验 | 保留为 G5/G6/G7 可复用部件与反例；出现同类产品残余时复用 |
| Wave 025 | 五次失败 smoke、一次结构路径闭合；资格结论仍无；正式 3,200 未运行 | 整体暂停、按需拆件复用，不再自动补完 |
| PT-001 D1/D2 | 三个合成任务与产品行为/评价合同已写；运行数为 0 | 仅作产品入口探针；不得替代完整 episode 集成 |

## 2. Wave 021：CE-001 公平基线

### 为什么启动

Wave 014–020 已分别给出若干局部任务结果，但这些结果来自不同世界、runner 和边界，不能直接换算成 A1–A5 的胜场。Wave 021 因此试图冻结一个共同外生包络，使不同 treatment 面对同一 Q、Target、Authority 分层、公开视图、预算、披露政策、故障语义、Effect 与 Acceptance 判据。

它要防止的核心错误包括：给某一 arm 多看答案、多一次重试或多一项接口；把不适用当执行失败；按 trace 第 N 个事件注入故障；用 occurrence 数量代替 exact Effect；跨不同 Authority stratum 选一个“总冠军”。

### 实际完成与结果

- 冻结 `BASELINE-CONTRACT.json` 与静态准入规则；机器状态只允许 `FAIRNESS_CONTRACT_ACCEPTED_NO_RUN_NO_WINNER`。
- 明确 A1 在 `P / PLURAL_INDEPENDENT` 中应为 `NOT_APPLICABLE`，不能替 owner 作决定；A2 则只能经共同 owner/Target API 行动。
- 冻结 exact task 的 object、Target、operation、46 个连续样本、功率、安全、噪声、时长、deadline、readback、双 Acceptance 与 finality 判据。
- 预注册多维结果向量：任务结果、唯一 Effect、Acceptance、错误行动、披露、协调、恢复和成本；禁止用单一总分覆盖安全与拒绝差异。
- 保存两类明确不公平 fixture：只给某一 arm oracle/额外预算/重跑机会；以及按 raw ordinal 注入并泄漏触发点。

实际比较运行数为 `0`，没有 candidate 被执行，没有比较结果，没有赢家。

### 后来暴露的假绿

Wave 023 对 Wave 021 validator 做重放后发现，它会接受至少五类运行时假绿：

1. 在未知 payload 字段中只给 A4 塞入 case、expected result、private truth 或 oracle；
2. plan 声明 `U`，实际 world 却是 `P`，A1 仍被列为可运行；
3. A3 实际发生巨量模型调用与隐藏检索，但仍自报无预算越界；
4. 各 arm 在看到成功或 grader 结果后再选择故障触发点；
5. executable 和 world 没有真正冻结，只在 manifest 中自报。

因此 Wave 021 的测试通过只证明静态字段和 profile 层面的准入性质，不能准入计分运行。这不是公平原则被反驳，而是其实现层级不足。

### 保留什么

- 同一完整任务、同一公开视图、同一 owner/Target 行动面、同一披露与故障语义；
- Authority stratum 内比较，不选跨 stratum 总冠军；
- `UNKNOWN`、refusal、`NOT_APPLICABLE` 与 failure 分开；
- exact Effect 与独立 Acceptance 不由 candidate/controller 自证；
- 任何横向结果必须来自新运行，不能把早期分散实验倒灌成胜场。

### 没有运行或不能推出什么

- A1/A2/A3/A5 没有在共同 blind world 中运行；A4 也没有在本合同下形成比较胜场；
- 三个组合臂 C1–C3 只被预注册，没有运行；
- A3 的真实 provider、A5 的真人、跨 arm clone、重复运行、置信区间和共同经济成本均不存在；
- 本地合成权威与数字 Target 不能推出法律权威、物理结果或现实主体接受。

### 产品意义与当前状态

Wave 021 留下的是“怎样避免不公平比较”的纪律，不是“我们产品应该怎么做”的答案。它曾把注意力引向全臂 tournament；当产品机制和完整 episode 尚未形成时，继续补齐全臂比较会让评价设施先于产品对象扩张。

当前状态：`PRESERVED_AS_COMPARISON_GUARD / PAUSED_ON_DEMAND`。只有一个已命名、高影响产品决定经过更小的任务评测仍无法判断时，才按该决定恢复必要部分，不恢复全套 tournament。

### 主要源路径

- `research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-021-fair-baselines/README.md`
- `research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-021-fair-baselines/AUDIT.md`
- `research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-021-fair-baselines/BASELINE-CONTRACT.json`
- `research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-021-fair-baselines/fixtures/`

## 3. Wave 022：从组件能力到完整行动链的语义闭合

### 为什么启动

在 Wave 014–021 之后，研究需要回答一个结构性问题：为什么检索、身份、策略、事务、授权、工作流、预留、幂等、撤销、补偿、回执和账本等能力都能找到，仍不能自动得到 V1/V2 要求的完整行动链？同时需要避免把“某个局部问题可被直接完成”错误写成“整体问题已解决”，也避免为了强调独特性而否认可复用组合的价值。

### 实际完成与结果

Wave 022 是一次来源受限的综合，没有启动新的 comparative run。它把整条链中容易被局部功能遮蔽的缺口分成六类：

1. **对象闭合**：搜索前，什么已经被表达成可搜索对象；
2. **任务语义闭合**：找到相似对象是否仍完成同一 Q、V0、Target 与底线；
3. **权威闭合**：身份、能力和相关性不能自动产生 Principal 的 Mandate；
4. **时序闭合**：搜索或授权在执行前是否仍 current；
5. **证据闭合**：相同终态是否来自正确 actor、operation 与 Target mutation；
6. **验收与生命周期闭合**：发生、被采用、被接受、结算与变化后恢复不能相互替代。

它还把 Wave 014–020 的结果放回各自作用域：本地数字 Target 的直接 actor 归因、统一平台直达、E2 条件形成、E3 ACK-lost reconcile/safe retry、E4 撤销后替代与有界重开、E6 受控进程终止后的迁移恢复。Wave 020 后续 root acceptance 使 E6 从初稿的 `Unknown` 更新为本地合成、受控 termination 下的有界接受，但没有改变真实跨机、硬崩溃、法律/物理边界及 V1/V2 未完成的结论。

### 假绿与漂移

Wave 022 正确指出了多个假闭合来源：相似结果替代原任务、workflow green 替代 Target Effect、中心/controller 代 owner 作决定、远端撤销记录替代 Target 已消费的 currentness、同一终态替代 actor 归因、发生替代 Acceptance。

它自身的漂移风险是：研究重心开始从“怎样完成一个新的完整 episode”转向“组件能力怎样归类、哪些残余值得自造”。这项综合有解释价值，但如果继续围绕分类扩写，就不会补出产品 episode。

### 保留什么

- 六类闭合作为产品链审查表；
- 局部结果必须标注 exact scope，不能向开放世界、法律、物理、生产和长期价值外推；
- 组件在正确 truth owner、时序和验收边界下形成的组合可以直接进入产品方案；
- 只有重复、可观察、影响原始价值且排除任务/接口/评价错误的精确 residual，才值得开新解法研究。

### 没有运行或不能推出什么

- Wave 022 本身没有新的 run、world、participant 或 Target result；
- E1/E5 在该综合的来源闭包内没有新判定；
- A1–A5 没有横向运行；
- 真实法律权威、物理 Effect、现实 Acceptance、长期漂移和生命周期净价值没有建立。

### 产品意义与当前状态

这轮最有用的产品含义是：最终产品必须包住六类闭合，并让用户看到当前哪一步还缺事实，而不是把若干功能入口并列摆放。它只能作为完整 RelationEpisode 的检查框架，不能成为单独研究主线。

当前状态：`PRESERVED_AS_SEMANTIC_CLOSURE_MAP / NO_CONTINUATION_AS_STANDALONE_LINE`。

### 主要源路径

- `research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-022-existing-tech-semantic-closure/SYNTHESIS.md`
- 其证据谱系回指 Wave 014–021 的各 `ROOT-ACCEPTANCE.md`、`INDEPENDENT-RED-TEAM.md` 与 Wave 021 `AUDIT.md`。

## 4. Wave 023：sealed-run admission

### 为什么启动

Wave 023 由 Wave 021 的五类假绿直接触发。目标不是再造一个更复杂的 runner，而是回答：在实际 candidate、world、启动面、Authority、故障触发、预算和结果 receipt 没有被真实绑定时，怎样阻止一份字段齐全的 manifest 冒充公平运行。

### 实际完成与结果

- 重现并保存 Wave 021 的五个假绿；
- 建立封闭字段、重复键拒绝、完整 Q preimage、candidate bundle、world/clone、launch surface、trigger、预算 ledger、顺序与停止规则的开发准入；
- 独立审计复验关键攻击，定向测试记录为 `38 passed`；
- 最高允许状态为 `DEVELOPMENT_SMOKE_ADMISSION_ACCEPTED_UNSCORED_NOT_EXECUTED`；
- 任何 `ACTUAL_COMPARISON` mode 都被无条件拒绝；comparison=`NOT_RUN`，evidence=`NONE`，winner=`NOT_EVALUATED`。

### 假绿与仍未关闭的门

Wave 023 把以下差异明确化：controller-shaped fixture 不是实际进程 receipt；fixture 自带的签名 key 只证明字节完整性，不证明权威；manifest 声明的 namespace/path/keyset 不是真实隔离；known-marker scan 不能排除编码或同义泄漏；一次未运行的 world×treatment fixture 不是 replicate；模型、人、Effect、Acceptance 和 finality 都必须有各自原生事实。

仍不存在 trusted controller/root seal、Principal key registry、commit-time currentness、真实 candidate、A3 provider、A5 真人、runtime-native Target/Acceptance receipts、真实 replicate closure 与共同经济成本。

### 保留什么

- “开发 smoke”和“实际比较证据”必须使用不同状态，不能通过改名升级；
- 运行对象要绑定实际传输字节、启动面、world、candidate、原生 trigger 与 budget ledger；
- known false-green attacks 应保留为最小回归；
- 缺少原生事实时必须 hard reject，而不是用 controller summary 补齐。

### 漂移与产品意义

Wave 023 的阻断判断是有价值的；但它也开启了从产品问题向通用证据平台扩建的明显漂移。sealed admission 只能保证将来某次比较的输入和证据资格，不能告诉我们 D1–D9 怎样工作，更不能产生一次 RelationEpisode。

当前状态：`FALSE_GREEN_REGRESSION_PRESERVED / GENERIC_ADMISSION_BUILD_PAUSED`。只有某项具体产品比较确实需要更强输入隔离和原生 receipt 时，才复用对应门。

### 没有运行或不能推出什么

- 没有 candidate launch、treatment presence、task success、Effect、Acceptance、cost 或 winner；
- S/R Authority twin 在 Wave 023 只冻结形状，没有执行；
- 不能据测试数、seal 或 schema 声称公平比较已开始。

### 主要源路径

- `research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-023-sealed-run-admission/README.md`
- `research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-023-sealed-run-admission/RED-TEAM.md`
- `research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-023-sealed-run-admission/INDEPENDENT-AUDIT.md`
- `research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-023-sealed-run-admission/A3-A5-PREFLIGHT.md`
- `research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-023-sealed-run-admission/RUN-CONTRACT.json`

## 5. Wave 024：Target-consumed Authority fence × ACK-lost recovery twin

### 为什么启动

Wave 023 只表达了一个高信息量 S/R 形状，Wave 024 把它缩成可运行的下游问题：在同一 exact Q、Target、operation、delegation、Effect 与 Acceptance 谱系中，Target 能否在同一持久状态机内区分“尚未消费 superseding fence”和“已消费并确认 fence”，并在 Target 形成终态后丢失 ACK、candidate 终止的情况下正确恢复。

它还加入 U 负控：Authority 已记录 revoke，但 Target 尚未安装并 ACK fence。U 用来阻止把远端撤销记录错误解释成全局即时 currentness。

### 实际运行与结果

最终 root acceptance 是 mixed scoped result：

| Claim | 结果 | 实际含义 |
|---|---|---|
| `TARGET-CONSUMED-AUTHORITY-FENCE` | `SUPPORT_SCOPED` | Target 已持久消费 matching fence 后，旧 epoch 请求在本地原子边界被拒绝且 Effect=0 |
| `EXACTLY-ONCE-RECOVERY` | `SUPPORT_SCOPED` | ACK 丢失和 candidate termination 后，S 从 exact status/readback reconcile 且不 replay；R 保持拒绝且不重试 |
| `NATIVE-POSTCONDITIONS` | `SUPPORT_SCOPED` | S 的 O_Q/O_V Acceptance 与 O_P finality 来自各自原生进程/store；R 对应项为 0 |
| `ISOMORPHIC-BLINDNESS` | `FAIL` | 固定 S→R→U 顺序、同 UID 文件/进程可见性与 timing side channel 未关闭 |
| `GLOBAL-AUTHORITY-CURRENTNESS` | `NOT_TESTED` | 本轮只证明 Target 已消费的本地 fence，不证明远端撤销后的全球即时失效 |

原生世界结果：

- S：Target `COMMITTED`，Effect=1，ACK 被 proxy 丢弃，恢复不 replay，Acceptance=2，finality=1；
- R：`Authority revoke → Target durable fence ACK → execute ingress`，Target `REJECTED_STALE_EPOCH`，Effect/Acceptance/finality/retry 均为 0；
- U：Authority 已 revoke、Target 未安装/ACK fence，Target raw `COMMITTED`，Effect=1、Acceptance=2、finality=1，但严格 `NOT_SCORED`。

U 是本轮最重要的负结果之一：远端 revoke、签名、workflow 或事后 owner receipt 不能补出不存在的跨域顺序。若产品要求更强 currentness，需要共享顺序、一次性 permit 或明确 lease/失效窗口，而不是增加发现或文档层。

### 假绿、重开与修复

旧运行 `twin-618415…` 一度看似闭合，但 Authority 只是把 controller 送入的 predecessor hash 签了名，没有自行验证 Target certificate、receipt signature 与 exact Q/object/Target/operation/epoch/head/decision/Effect。该运行因此被重开并保留为失败历史，不进入证据闭包。

修复后的 Authority 在启动时固定 lab root，接收完整 Target receipt，独立验签和核对 exact scope 后才签 successor revocation；六类“签名有效但 predecessor 语义错误”的攻击 fail closed。独立 evaluator 不导入 runtime，从原生 SQLite、签名、hash 与 receipt 链重算；记录为 runtime 24 项、evaluator 10 项通过。测试数量只支持这些具体软件契约。

### 保留什么

- `versioned delegation/revocation + Target-consumed monotonic fence + Target-local atomic decision/Effect-or-refusal ledger + stable idempotent request + exact status/readback + native Acceptance/finality` 这一有界组合；
- U 作为传播未完成时不能评分为 current/revoked 的长期反例；
- owner/Authority 必须独立验证 predecessor 语义，不能签 controller 给出的字符串；
- ACK 丢失后先 readback，再决定 reconcile、停止或 retry。

### 没有运行或不能推出什么

- Target 自身 crash/restart 后 fence 单调性未检验；
- 并发线性化的所有 interleaving、semantic alias、旁路 endpoint 与 transient Effect 未闭合；
- hostile same-UID、外部 append-only root、真实跨机、法律权威、物理 Effect、生产长期性未建立；
- A1–A5/C1–C3 比较运行仍为 0，winner 为 none；
- 完整 RelationEpisode、G1–G4 的入口/形成、RelationEcology 均未由本 twin 检验。

### 产品意义与当前状态

Wave 024 是 Wave 021–025 中唯一直接产生可复用产品下游能力证据的一轮。它可以进入完整 episode 的 Authority、执行、Effect/readback 与 Acceptance 边界，但它不是产品闭环。blindness 失败不抹掉前三项能力支持，前三项通过也不能掩盖 blindness 失败。

当前状态：`SCOPED_COMPONENT_RESULT_RETAINED / EXPAND_ONLY_IF_EPISODE_EXPOSES_SAME_RESIDUAL`。不再为了完成 Wave 编号主动扩展；当完整产品 episode 在撤销、ACK-lost 或 stale epoch 上出现同类断点时，直接复用本组合与 U 负控。

### 主要源路径

- `research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-024-authority-epoch-twin/QUESTION.md`
- `research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-024-authority-epoch-twin/DESIGN.md`
- `research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-024-authority-epoch-twin/README.md`
- `research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-024-authority-epoch-twin/INDEPENDENT-AUDIT.md`
- `research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-024-authority-epoch-twin/ROOT-ACCEPTANCE.md`
- `research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-024-authority-epoch-twin/TRANSFER-MATRIX.md`

## 6. Wave 025：盲比较资格挑战

### 为什么启动

Wave 024 证明“payload、argv、env 和 state path 看起来一样”仍不足以支持 blindness。Wave 025 因此在 A1–A5 比较之前，试图用隔离 cell、秘密随机化、host observation、leak-only collector、正控与独立 evaluator 检验 `T0 SEALED → T1 PUBLIC-PREIMAGE` 这一前缀阶段是否泄漏 hidden role。

冻结问题明确把 full comparison qualification 保持为 `NOT_TESTED`；即使 prefix 通过，也仍需 dynamic broker、earliest lawful divergence、actual treatment observation regime、A3 provider、A5 human、Authority/applicability 和 evaluator feedback 的后续资格。

### 实际完成与结果

Wave 025 没有形成 qualification verdict。最重要的实际运行谱系是五次被保留的失败 smoke 与一次结构闭合 smoke：

| 批次 | 实际结果 | 改变的判断 |
|---|---|---|
| A | Docker Desktop 拒绝显式 `--pid private`，首 slot 前 `ABORTED` | 命令语法不能由其他 runtime 经验推断，本机实际配置须由 inspect 证明 |
| B | Docker Desktop 拒绝显式 `--uts private`，首 slot 前 `ABORTED` | 同上 |
| C | prepare 绑定错误 feature-spec hash，锚定和运行前发现 | 保留为 `PREPARED_INVALID_UNANCHORED`，不能修补后续跑 |
| D | collector 12/12 exit 0，但 stopped container 的 `/out` tmpfs 无法用 archive path 读取 | stdout 绿灯不能替代证据取回闭包 |
| E | supervisor 证明 container 仍运行且 ready，但 archive API 仍看不到 tmpfs | running/stopped 两种 archive 假设均被实际反例否定 |
| F | V1.3 post-cut protocol 12/12 `COMPLETE`，reveal 可重建 | 只支持 runner/evidence structural path；旧 evaluator 因 schema/profile 不兼容正确返回 `NOT_QUALIFIED` |

F 没有 formal 人口，也没有执行最后选择的完整 attack profile。其结果不能支持 detector sensitivity、T equivalence、prefix qualification 或任何 treatment 比较。

随后完成的研究设计包括：

- 选择完整叶级 `EXECUTABLE-ATTACK-PROFILE.json`，保留 F01–F07 与 C01–C05；这是方法选择，不是结果；
- 因五个 gated attacks 的联合 false-fail 校正，将 formal population 从历史 1,600 修正为 3,200；3,200 从未运行；
- actual-shape benchmark 显示完整 extraction 仍是分钟级线索，真正高成本的是 9,999 次全模型重训；benchmark 不是完整 evaluator rehearsal；
- 多个子研究保留了 feature/provider、C01 interaction、model-input、确定性数学与 collector receipt 的反例和候选，但 `MODEL_INPUT_NOT_CANON`、`G_NOT_AUTHORIZED`、`FORMAL_3200_NOT_RUN`。

### 最重要的假绿与负结果

1. **记录面相同不等于实际观察面相同。** 固定顺序、共享 UID、路径、进程、cache 和 timing 都可能泄漏。
2. **collector 绿不等于真实 treatment 盲。** 专有模型、binary、adapter 或 prompt 可能预置 key，解码 `nonce || HMAC_K(nonce, hidden_truth)`；普通 collector 只看到随机 token，真实 treatment 却能恢复 role。
3. **两个独立实现都“符合文字合同”不等于检验同一 claim。** feature-spec 与独立 evaluator 的 feature、树、kNN、logistic、permutation 和 CI 语义显著不同；同时绑定两个 hash 不能消除分歧。
4. **测试、样本设计和 seal 不是资格结果。** 正控是否被检出、T 是否低于阈值、动态 broker 是否合格都没有 formal 运行证据。
5. **更复杂不自动更严。** 完整叶方案与压缩方案各有遗漏/成本；选择 profile 只冻结待测对象，不证明其有效。

### 漂移

Wave 025 从一个必要的 blindness 反例出发，逐步扩张为通用 runner、3,200-slot 统计设计、feature universe、C01–C05、双 provider、确定性数学、receipt schema 与安全边界研究。每个子问题都可能合理，但它们没有绑定一个当前必须决定的产品机制，也没有推进完整 RelationEpisode。继续补齐会把实验室资格系统当成产品主线。

### 保留什么

- A–F smoke 的完整失败谱系，尤其 archive/tmpfs 与 post-cut extraction 的真实边界；
- prefix、dynamic lawful divergence、native treatment regime、evaluator freeze 和跨 session contamination 的分层；
- current-run canary 与 predecessor contamination 两类正控不能互相替代；
- actual treatment 必须按其真实 artifact/launcher/UI/credential 重新资格，collector 结果不能无条件迁移；
- 只有命名产品决定经过小型任务评测仍无法判断时，才复用 frozen packet、runner、holdout、feature 或统计部件。

### 没有运行或不能推出什么

- formal 3,200 batch、完整 profile、双 replay、动态资格、真实 A1–A5/C1–C3 均未运行；
- A3 provider、A5 human session、成本 Pareto、winner 均不存在；
- `PREFIX_QUALIFIED_SCOPED` 未取得；full blind comparison qualification 明确未检验；
- 网络/主机/权限攻击、安全保证、生产隔离不在本研究可宣称范围。

### 产品意义与当前状态

Wave 025 的价值是保留假绿、运行时事实和可按需复用的测量部件。它没有产生面向用户的解决能力，也没有证明任何产品路径更好。

当前状态：`PREFLIGHT_HISTORY_PRESERVED / GENERIC_COMPLETION_PAUSED / COMPONENTS_ON_DEMAND`。恢复条件必须同时满足：已有一个明确产品决定；更小、靠近任务的 paired/removal/owner-readback 评测仍不能决定；Wave 025 的某个具体部件会改变该决定；其成本低于选错机制的代价。否则保持暂停。

### 主要源路径

- `research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-025-blind-comparison-qualification/QUESTION.md`
- `research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-025-blind-comparison-qualification/PRE-RUN-SYNTHESIS.md`
- `research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-025-blind-comparison-qualification/INTEGRATION-FINDINGS.md`
- `research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-025-blind-comparison-qualification/SMOKE-LEDGER.md`
- `research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-025-blind-comparison-qualification/ACTUAL-SHAPE-BENCHMARK.md`
- `research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-025-blind-comparison-qualification/PROFILE-SELECTION.md`
- `research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-025-blind-comparison-qualification/QUALIFICATION-CONTRACT.md`
- `research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-025-blind-comparison-qualification/POWER-NOTE.md`
- `research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-025-blind-comparison-qualification/feature-spec/`
- `research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-025-blind-comparison-qualification/independent-evaluator/`

## 7. PT-001：D1/D2 第一轮产品入口探针

### 为什么启动

PT-001 是对前述漂移的产品回拉：不再先问通用 evaluator 能做到多强，而是先问一个普通用户怎样从模糊目标进入可行动链。它试图为两个入口决定准备最小任务证据：

- D1：怎样澄清目标、保留底线、Unknown 和拒绝，同时避免无休止问卷或模型擅自改写；
- D2：怎样在目标被 member-check 后形成少量下一步候选，何时 direct path 已足够，何时目录、本地 projection 或有界询问才增加价值。

### 已经写成什么

1. `TASK-SPEC.md`：三个异质合成任务——两周内的可触摸展示样机、易损展品运输与就位、离开十天期间的社区花园照料。每例分离 solver-visible `FUZZY-INPUT` 与 evaluator-private `TASK-ORACLE`，并包含 direct 正控、未表达机会、decoy、stale、refusal/Unknown、Effect owner 与 Acceptance owner 的设计压力。
2. `PRODUCT-ARMS.md`：D1 的 interview、hypothesis+check、permitted-context+check，以及 D2 的 index、projection、compose 产品行为；D2 不实际向外部联系，只能提出下一步询问。
3. `EVALUATION-CONTRACT.md`：逐目标元素、必要条件、问题负担、Unknown/refusal、机会、披露、误唤醒与 path progression 评价；设置目标改写、拒绝擦除、越界披露、虚假推进、遗漏关键条件等结构性阻断，不以平均分抵消底线失败。

这些是 authoring candidate 和 first-run design，不是运行结果。

### 当前实际结果

```text
TASKS_AUTHORED = 3 SYNTHETIC CANDIDATES
D1_RUNS = 0
D2_RUNS = 0
REAL_USERS = 0
EXTERNAL_PROBES = 0
RELATION_EPISODES_COMPLETED = 0
EFFECT_RESULTS = 0
ACCEPTANCE_RESULTS = 0
PRODUCT_DECISIONS = NONE
```

因此 PT-001 不能支持某个澄清方式、目录、本地 projection、模型、人工或组合已经更好，也不能支持现实覆盖率、现实效用或安全性。

### 它在最初规划中的准确位置

PT-001 D1/D2 只处于完整 RelationEpisode 的**入口适配层**：

```text
模糊输入
  → 用户仍认领的目标草稿
  → 承重条件被确认或显式保持 Unknown
  → 一个合法、可验证、未冒充同意的下一步候选
  → 交给共同提案、能力资格化、Authority/Reservation、Commitment、执行、Effect、Acceptance 与重开
```

其终点是“合格的 episode 入口”，不是关系形成、授权、执行、Effect、Acceptance 或完成。D1/D2 即使全部通过，也只能说明入口行为在三个合成世界中守住了目标与披露边界，不能宣称完整产品问题解决。

### 假绿与漂移风险

- oracle、隐藏条件或正确路线进入 solver-visible packet，会使运行无效；
- 把“准备询问”“搜索命中”“模型猜测”写成对方 ACK、能力、同意或机会形成，是虚假推进；
- direct path 已满足时仍制造多方协作，是负增益；
- 把目录缺失当世界无路、把拒绝披露当无需求、把海报等易完成代理目标当原目标，都会制造假成功；
- 若继续扩大任务库、arm、classifier 或样本量，而不接入后续 RelationEpisode，就会把入口探针重新变成独立主线。

### 保留什么

- 三个合成任务中的真实产品压力：目标保真、direct 正控、stale/decoy、有限披露、未表达机会、拒绝和 owner 分离；
- truth/solver 分离与结构性阻断项；
- D1/D2 产品行为作为一次小型 fresh probe 的候选；
- 停止规则：一旦足以决定入口默认组合，停止扩建 evaluator，立即接入后续 episode。

### 什么没有运行、当前怎样暂停

- 五个 D1 fresh 变体与两个 D2 hidden world 只是合同要求，尚未生成完整独立运行包并执行；
- 三个 D1、三个 D2 arm 没有 fresh transcript 或 evaluator return；
- 没有真实用户 member-check，没有 recipient 原生回复，也没有现实 Effect/readback/Acceptance；
- 不恢复 Wave 025 的 3,200、C01–C05 或 full qualification 来启动 PT-001。

当前状态：`ENTRY_PROBE_AUTHORED_NOT_RUN / PAUSED_AS_STANDALONE_LINE / AVAILABLE_FOR_ONE_BOUNDED_RUN`。只有完整 episode 锚点缺少合法入口时，才运行一次最小 D1/D2 probe；一旦形成入口，立即交给同一 episode 的后续链，不再独立扩张。

### 主要源路径

- `research/projects/joint-action-formation/experiments/pt001-first-product-evaluation/TASK-SPEC.md`
- `research/projects/joint-action-formation/experiments/pt001-first-product-evaluation/PRODUCT-ARMS.md`
- `research/projects/joint-action-formation/experiments/pt001-first-product-evaluation/EVALUATION-CONTRACT.md`
- 定位综合：`research/projects/joint-action-formation/studies/product-chain-t1-t3/SYNTHESIS.md`

## 8. 跨轮保留与停止规则

### 作为产品链能力保留

- Wave 022 的六类闭合检查；
- Wave 024 的 Target-consumed fence、exact status/readback、ACK-lost no-replay 与 owner-native postconditions；
- PT-001 的目标保真、typed Unknown、有限披露、direct 正控和“候选不等于同意”入口约束。

### 作为反例与回归保留

- Wave 021/023 的 payload oracle、world 声明错配、隐藏预算、post-grader trigger、未冻结 executable/world；
- Wave 024 的 U 世界、Authority 对 predecessor 只签 hash、固定顺序/同 UID blindness 失败；
- Wave 025 A–F smoke、archive/tmpfs 失败、独立实现语义不一致、keyed decoder 反例；
- PT-001 的目标改写、拒绝擦除、stale/decoy、虚构推进与 direct-negative-control failure。

### 不再把什么当成果

- 文件、schema、seal、hash、测试数、样本设计、runner 跑通或 classifier 数量；
- `PLANNED`、`PRECOMMITTED`、`ADMISSION_ACCEPTED`、`STRUCTURAL_SMOKE_COMPLETE`；
- 合成 world 中的字段齐全或模型生成的“成功”叙述；
- 一项下游 twin 通过后对完整 RelationEpisode 的外推。

### 恢复条件

后续只有两种恢复方式：

1. **产品直接调用**：完整 episode 在 Authority、Effect、Acceptance、撤销或 ACK-lost 上出现与 Wave 024 同构的断点，复用对应部件和反例；
2. **决策仍不可区分**：一个已命名、高影响产品选择经真实任务、小型 fresh holdout、paired/removal 和 owner-native readback 后仍然 Unknown，再按该残余调用 Wave 021/023/025 的某个必要部件。

除此之外，Wave 021、023、025 不主动续建；Wave 022 不另开实验；PT-001 D1/D2 不成为新主线。当前主线应回到：用一个合法入口完成同一 RelationEpisode 的共同提案、能力、Authority、Commitment、真实执行、Effect、Acceptance 与失败后重开。
