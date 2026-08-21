# Wave 022：已有技术为什么存在，却没有自动闭合 V1/V2 问题

日期：2026-07-30  
状态：`INDEPENDENT_SYNTHESIS + POST_WAVE020_ACCEPTANCE_UPDATE / NO COMPARATIVE RUN / NO V1_V2_COMPLETION CLAIM`

> **后续证据更新（2026-07-30）**：本综合初稿冻结时，Wave 020 仍在独立攻击中，所以正文
> 原始推导把完整 E6 保持为 `Unknown`。随后 root 修复并保留九类假绿，使用当前实现从零生成
> `suite-688917cb80094ed49d5f8e4195a811a8`，25 项攻击通过，15 个 formal SQLite 均为
> standalone DELETE `01/01`，最终 root acceptance 接受
> `LOCAL_SYNTHETIC_E6_EXISTING_DURABLE_WORKFLOW_LEDGER_FENCE_SCOPED_SOLUTION`。
> 本文所有与此冲突的 “E6 Unknown” 句子应按第 G 节和证据表的更新结论读取；该更新不改变
> A1–A5 尚未横向运行、真实物理/法律/跨机边界未建立以及 V1/V2 未解决的结论。

## 一、结论先行

当前证据支持的答案不是“现有技术不行”，也不是“只有通爻能解决”。

更准确的结论是：

> 大量成熟技术已经分别提供了检索、目录、身份、策略、事务、授权、工作流、预留、
> 幂等、撤销、补偿、状态查询、回执、人工审批和持久账本等能力；但这些能力通常从
> **对象已经被表达、角色已经被定义、权威边界已经被编译、目标已经可操作**的地方开始。
> V1/V2 追问的则是：在多个 Principal 的局部世界、权威、披露策略和责任不能安全折叠时，
> 怎样判断路径是既存、需要创造条件，还是需要重写问题；又怎样把形成、执行、Effect、
> Adoption、Acceptance、Settlement、撤销和重开闭合为同一个可归因、可复核的行动链。

Wave 014–020 已经给出几个重要的正向结果：

1. 在精确、冻结的局部问题内，现有成熟技术能够完整解决问题；
2. 有些问题由平台原生能力直接解决，不需要额外关系形成；
3. 有些问题不是缺少新原语，而是此前没有把已有原语按正确的 owner、时序、证据和验收语义
   组合起来；
4. “组合、收敛并可复现地解决”本身就是通爻方案，不是次等成功；
5. 当前正式接受材料没有建立“某个 residual 已确认只能靠全新机制解决”的结论。

但这同样不等于 V1/V2 已经完成。E6 只在本地合成、受控 process termination 条件下被接受，
A1–A5 公平横向比较尚未运行；不可预告物理硬崩溃、真实跨机 transport、真实法律 Authority、
物理 Effect、现实主体 Acceptance、长期漂移与净价值也尚未由这些实验建立。

因此，本轮最重要的研究纪律是：

```text
已有技术完整解决      -> 正向成果，直接采用
已有技术组合后解决    -> 正向成果，组合即方案
已有技术尚未验证      -> 保持 Unknown，先做同条件验证
同条件成熟方案被反驳  -> 才定位精确 residual，并判断扩展、重构或创新
```

## 二、本综合回答什么，不回答什么

本综合只回答一个结构性问题：

> 为什么成熟原语普遍存在，却没有因此自动得到 V1/V2 所要求的共同可行动性闭合？

它不尝试证明“产业界从未有人组合过这些技术”。当前材料不是对所有平台、协议和组织制度的
历史普查，不能支持这种全称判断。它能够支持的是：

- 各类成熟原语与 V1/V2 完整任务之间存在明确的作用域差；
- 在精确任务、owner topology、时序和证据要求被显式冻结后，若干 residual 确实可由成熟
  组合关闭；
- 被关闭的是有界局部问题，不应向法律、物理、跨域、长期或开放世界整体外推；
- 尚未运行的公平比较不能被口头推断成任何方案胜出。

本综合采用：

- 当前 `ACTIVE` 的 Problem V2；
- 被 V2 逐哈希继承的 V1 candidate；
- Wave 014–020 的正式 root acceptance；
- Wave 021 的公平基线合同与审计。

本综合没有读取或继承尚未进入上述正式闭包的候选结论，也没有引入外部模型返回作为证据。

## 三、真正缺的通常不是“一个功能”，而是六种闭合

### 1. 对象闭合：搜索之前，什么已经成为可搜索对象

搜索、RAG、目录和 Agent Card 都需要某种可索引对象：查询、文档、资源描述、能力声明、
接口或卡片。它们可以从已经表达的对象中提高召回、排序和定位效率，却不能单独证明：

- 未表达的 Intent 已经存在；
- Intent 的生成者就是所代表的 Principal；
- 受益者、受影响者和有权决定者相同；
- 一个候选能力在当前条件下真的可用；
- 原本不存在的权限、承诺、预留或可执行条件已经形成。

V2 允许上游系统产生隐式 Intent，但明确把上游生成过程放在当前协调接口范围外。Intent 到达
接口后，可以携带可验证的 Principal、Mandate 和 provenance，也可以保持 `Unknown`；接口
不能只凭到达就推断认领、授权或接受。

所以，“必须先清楚自己想要什么”不应被理解为每个主体都要预先写出完整形式规格。更精确的
要求是：

> 在某个机制要据此采取行动之前，至少要有足够的显式语义来界定它正在代表谁、寻找什么、
> 能改变什么、不能改变什么、由谁决定，以及什么证据算成功。

在此之前，目录可以帮助探索，不能替尚未建立的规范状态背书。

### 2. 任务语义闭合：找到“像是相关的对象”不等于完成同一个任务

V1 要求冻结 \(S_0\)、原始价值 \(V_0\)、资格谓词 \(Q\)、必要 Principal、Authority
Locus、目标 witness 和可比较基线。路径可能是：

- 原本存在、只是没有发现；
- 通过改变工具、权限、伙伴、资源或现实条件首次形成；
- 通过降低价值底线、改写 \(Q\) 或遗漏主体而变成另一个问题。

如果不冻结这些语义，任何检索或规划系统都可能通过“找到了相似结果”制造假成功。Wave 021
进一步把 CE-001 的 exact Effect 固定为 C7、46 个连续样本、其他线路为空、功率/安全/噪声/
时长/deadline 全部满足，并绑定 readback、Acceptance 与 finality。这说明“产生一个
occurrence”远远不够，必须确认它仍是原任务。

### 3. 权威闭合：能力、身份和相关性都不能自动产生 Mandate

Agent Card 可以声明能力，目录可以定位 endpoint，认证可以确认某个 key，模型可以生成计划；
它们都不能自动推出：

- 某个 Principal 已认领该 Intent；
- 某个 actor 有权代表 owner 作出决定；
- 允许的范围、期限、用途和条件；
- 受影响主体已经同意；
- 拒绝可以被忽略。

Wave 019 的 E2 之所以需要独立 owner process、各自的签名响应、O_R 的 `COUNTER`、显式接受、
purpose-scoped grant、reservation 与 commit-time current-head revalidation，正是因为
“候选方案看起来合理”不能代替 owner-native act。移除 formation operator 或收到有效
`REFUSE` 时，后续 formation 和 Target descendants 必须全部为零。

### 4. 时序闭合：昨天正确、提交前可能已经失效

动态世界的核心问题不只是索引变旧。Authority、capability、reservation、revocation、
policy head、Target version 和承诺都可能在搜索完成后、执行前发生变化。

Wave 016 和 Wave 018 显示了两个不同的时序缺口：

- ACK 丢失以后，“没有收到成功”不等于“没有发生提交”；
- primary 在提交前被撤销以后，旧 offer 或旧 `current=true` 不能继续穿透到执行。

因此，候选发现必须与 commit-time current owner head、Target status/readback、capability
freshness、幂等 identity、撤销和补偿机制闭合。只维护静态索引快照不能完成这一点。

### 5. 证据闭合：同样的终态可能来自不同 actor、不同权限和不同路径

Wave 014 的 causal twin 给出最清楚的反例：A4 直接提交和 Helper 直接提交能够产生完全相同
的 Target 终态。只看终态，两者都会被误判为 A4 成功。

Target-native atomic mutation receipt 与 authoritative readback 绑定 actor、request、
operation、pre/post state、version 和 commit，才区分：

- `TaskOutcomeSatisfied`；
- `AuthorizedExecutionCommitted`；
- `EffectAttributableToArm`。

这不是要求所有系统都发明新的因果理论，而是指出：若评价问题包含直接 actor 归因，就必须
把 truth owner 放在能够观察原子提交的 Target 边界；搜索结果、模型解释、Router 自报和相同
终态都不能替代这一证据。

### 6. 验收与生命周期闭合：发生了，不等于被认领、接受、结算或可恢复

V1/V2 明确区分：

`Capability → Mandate → Commitment → Execution → Effect → Adoption → Acceptance → Settlement`

这些阶段可以分别失败。成熟系统经常擅长其中一段，例如：

- 搜索和目录负责候选发现；
- IAM 负责某个已建模域内的 policy decision；
- workflow 负责执行已定义流程；
- transaction/ledger 负责原子状态；
- saga/compensation 负责部分恢复。

但完整任务还可能要求受益者和场所 owner 的双 Acceptance、finality、撤销后的局部重开、
替代方重新发现、补偿、争议与退出。Wave 017 只有在合法统一平台已经预编译角色、Authority、
Target 和验收时，才能用一次 native call 完成；Wave 018 则必须在撤销后重新打开必要部分。

## 四、为什么“他们都有”，仍然没有自动解决我们提出的问题

把上述六种闭合放在一起，可以得到一个更建设性的回答。

### 1. 很多成熟技术的起点，正是 V1/V2 要研究怎样形成的东西

workflow 假定流程已定义；IAM 假定 subject、resource、action 和 policy 已建模；目录假定
资源已描述；transaction 假定操作和 authoritative store 已确定；Acceptance 系统假定
验收者和标准已知。

这不是这些技术的缺陷。它们在自己的作用域内非常强，甚至可以完整解决问题。差异在于，
开放、低频、异构关系中，角色、伙伴、条件、权限、验收方式和依赖本身可能尚未被编译。

### 2. “各自有一个原语”不等于“存在一个共同的真相闭包”

如果目录、IAM、workflow、ledger、owner status 和 Acceptance 分别维护不同对象、版本和
身份，局部绿灯可以同时成立，而系统任务仍失败。Wave 015 初版已经暴露这种情况：

- hidden controller 和 ArmViewFactory 各有 allowlist；
- 组件 view 无法直接交给真实 launcher；
- private scanner 只检查整包而可能漏嵌套字段；
- private receipt 只能由原 controller 对象验证；
- 名为 ledger 的对象若没有真实持久 Target truth，不能承担 mutation 事实。

最终接受来自把它们收敛为一个 arm schema、一个 Broker surface、一个 Target truth store 和
可独立重验的凭据链。这里的价值就是组合与语义收敛，不是创造 SQLite、CAS 或签名算法。

### 3. 预编译平台已经解决稳定分布，但不会因此覆盖开放长尾

Wave 017 证明：在 `U / LAWFULLY_UNIFIED` 条件下，平台原生 policy/IAM、内部资源锁和成熟
Target ledger 可以直接完整解决 E0，且不发生 discovery、relation、delegation 或 external
transfer。

这应被视为理想正向结果：稳定、高频、边界明确的路径就应该被编译成平台或中心能力。

但同一结论不能外推到 `P / PLURAL_INDEPENDENT`。Wave 021 明确规定 A1 lawful center 在
`P` 中必须是 `NOT_APPLICABLE`，不能代 owner 签名。这里的问题不是中心算力不足，而是不存在
可合法集中的 Authority。不同 Authority stratum 不能选一个跨层“总冠军”。

### 4. 动态失败发生在组件之间，而不是单个组件内部

ACK-lost、撤销、stale head、替代方出现、commit-time policy 变化和 crash migration 都是
跨组件、跨时间的边界事件。一个目录可能正确返回候选，一个 IAM 决策可能当时有效，一个
workflow 也可能按规则执行，但它们之间没有 freshness、idempotency、reopen、fence 和
Target evidence 闭合时，仍会出现重复 Effect、越权继续、错误拒绝或无法恢复。

Wave 016 和 Wave 018 的价值就在于把这些“组件之间的缝”变成可复现的 paired world 与
removal world，而不是再证明一次幂等或撤销概念存在。

### 5. 现实组织往往用高语境人力填补这些缝，所以系统表面上“能用”

V1 已经指出，低频异构关系的主要成本并不只是 token 或检索，而是问题、角色、合同、规则、
审批、接口和验收标准的形成，以及高语境人员的解释、例外与责任判断。

因此，很多现成系统可能通过平台运营、管理员、项目经理、法务、工程师或协调者在系统外补齐
语义。系统完成了下游机械执行，却没有把上游 material judgment 变成可复用、可验证、可
重开的机制。

这是一项从 V1 问题结构推出的解释，不是对所有现实平台运营方式的经验统计。后续仍需要真实
任务和成本数据验证：通爻式组合究竟降低了这些边际判断成本，还是只把成本转移成新的边界
表达、接入、证据和治理负担。

### 6. 以前“没有解决”不能用产品是否宣称了某个协议判断

一个系统可能没有使用通爻术语，却已经完整解决某个有界问题；Wave 017 就是这种结果。反过来，
一个系统即使提供 Agent Card、目录、发现、协作协议或模型编排，也不能只凭功能名称被算作
V1/V2 完成。

正确判断单位始终是：

> 在环境与前提 \(E\) 下，针对同一问题 \(P\)，机制或组合 \(M\) 是否提供所需能力 \(C\)，
> 满足要求 \(R\)，并在失败反例 \(F\) 和替代方案 \(A\) 下仍然成立。

## 五、逐案拆解：原语、缺口、闭合结果与非主张

### A. Wave 014：相同终态下的直接提交者归因

**已经存在的成熟原语**

- Target/reference-monitor 边界；
- 原子 mutation receipt；
- authoritative readback；
- actor/request/operation/version/commit 绑定；
- 签名与内容哈希。

**此前未闭合的语义**

- 评价器把“终态满足”误当成“A4 直接造成”；
- Router 或 Helper 的解释可能覆盖真实 actor；
- state projection、readback 与 commit provenance 没有形成唯一一致链。

**接受结果**

Target-native atomic mutation receipt + authoritative readback 足以在该本地数字 Target
边界区分 A4 direct commit 与 Helper direct commit。这个 residual 已由成熟 target 路线
关闭，不需要通爻独占的 mutation 机制。

**非主张**

不证明法律 Authority、物理 Effect、Acceptance/Settlement、恶意同机管理员下不可篡改、
公平 arms 或 V1/V2。

### B. Wave 015：剩余案例 runner 的组件基础

**已经存在的成熟原语**

- SQLite `BEGIN IMMEDIATE`；
- CAS；
- one-shot capability；
- HMAC/Ed25519 receipt 与 readback；
- blind child launch；
- broker、allowlist view 与 hidden controller。

**此前未闭合的语义**

- 多套 allowlist 和不兼容 view；
- 嵌套 private scalar 泄漏；
- controller receipt 不能离线独立验证；
- H-first 相同终态、并发冲突、replay 和 capability consumption 没有落入同一个 Target
  truth store。

**接受结果**

成熟 SQLite + CAS + one-shot capability + stored authenticated receipt/readback 已关闭
本地数字 Target 的 direct commit attribution、exact-once 和 concurrency residual，并形成
E3/E4/E6 所需的部分公共基础。

**非主张**

Wave 015 不是 E3/E4/E6 任务成功。尤其 E6 probe 只建立 blind launch、hidden trigger、
capsule/fence 的本地进程闭环，没有 Target ledger、完整 durable history、真实 migration、
owner-head revalidation、Acceptance 或 finality。

### C. E0 / Wave 017：合法统一平台直接完成

**已经存在的成熟原语**

- 平台原生 policy/IAM；
- 内部资源锁；
- 成熟 Target ledger；
- 双角色 Acceptance 与 finality。

**此前是否需要开放形成**

不需要。在 `U / LAWFULLY_UNIFIED` 冻结世界中，角色、Authority、操作、Target 和验收已经
由平台预编译。

**接受结果**

一次 native call 完成 exact digital task，Target 只提交一次，removal world 在移除 signed
direct Authority 后 policy 拒绝且零 Effect。discovery、relation、delegation、external
transfer 均为零。

这是一项“成熟平台直接完整解决”的正向成果，说明通爻不应为同一能力再造开放关系机制。

**非主张**

不外推到 `P / PLURAL_INDEPENDENT`、物理送电、CE-001 全 family、长期维护/停更/迁移或净
经济成本。

### D. E2 / Wave 019：从 S0 空状态首次形成必要条件

**已经存在的成熟原语**

- workflow；
- HITL 审批；
- purpose-scoped grant；
- reservation；
- policy gate；
- durable Target ledger；
- owner 签名状态与拒绝。

**此前未闭合的语义**

- S0 中哪些条件确实不存在；
- proposal 的 exact canonical bytes；
- 谁有权形成 purpose token、delegation、commitment、reservation 和 safety 条件；
- `COUNTER` 怎样被明确接受；
- owner act 与 controller/broker 提议怎样分离；
- commit-time owner head 是否仍为 current；
- Target exact Effect、双 Acceptance 和 finality；
- remove/refuse 后是否确实阻断全部 descendants。

**接受结果**

成熟 workflow + 独立 HITL owner act + scoped grant + reservation + commit-time gate 在
local-synthetic E2 世界首次形成必要条件，并只产生一次 exact C7 digital occurrence。移除
operator 或 owner 签名拒绝会阻断 formation 与 Target descendants。

这说明 E2 的当前局部解法是已有技术的正确组合与语义收敛，不是单一新协议。

**非主张**

不证明法律 Authority、现实 Principal 身份、物理 Effect、外部 PKI、生产可靠性、跨域
泛化、长期漂移或净经济价值。

### E. E3A/E3B / Wave 016：ACK 丢失后的 reconcile 与 safe retry

**已经存在的成熟原语**

- Target operation ledger；
- exact signed status/readback；
- one-shot capability；
- capability freshness；
- idempotent retry。

**此前未闭合的语义**

- readback 前两世界必须具有相同可见 prefix；
- `NOT_COMMITTED` 必须覆盖 current head，而不是普通 404；
- wrong-object decoy 必须被排除；
- 已提交世界只能 reconcile，不能 replay；
- 未提交世界必须先获得 fresh capability，再保留 operation identity 安全重试；
- 两世界各自只能产生一个 exact mutation。

**接受结果**

成熟组合已经区分 ACK 丢失后的“已经提交”和“尚未提交”，分别执行 no-replay reconcile 与
freshness-gated safe retry；E3A/E3B 各自产生一次 exact digital mutation。

**非主张**

不证明物理 Effect、法律 Authority、外部 PKI、恶意同权限 writer、生产长期可靠性、relation
formation 或正式机制晋升。

### F. E4 / Wave 018：撤销、替代方与有界局部重开

**已经存在的成熟原语**

- revocation；
- bounded reopen；
- compensation；
- rediscovery；
- owner receipts；
- fresh status；
- durable idempotent ledger。

**此前未闭合的语义**

- alternative 在 revoke 前不能被 controller 预选或泄漏；
- primary 被撤销后，旧状态不能穿透到 commit；
- 替代方必须通过 owner-native rediscovery 实际出现；
- reopen 只能沿必要依赖展开，不能重做全局；
- commit 前必须查询各 owner 最新 head；
- success world 要 exact Effect、双 Acceptance、alternative-bound finality；
- remove-alternative world 要 bounded refusal 且 Target 不变。

**接受结果**

成熟组合在 local-synthetic E4 世界完成撤销后的合法替代、补偿、重新发现、current-head
重验与 exact-once Target Effect；移除 alternative 后正确退化为 bounded refusal。

**非主张**

不证明现实法律含义、物理 resource/actuator/meter、真人理解与接受、provider 停更/迁移/
许可/锁定、跨组织部署或 V1/V2。

### G. E6：崩溃、迁移与旧执行者隔离

**已经存在的成熟原语**

- durable history 与 SQLite formal snapshot；
- signed recovery capsule；
- Target ledger、receipt 与 authoritative readback；
- persistent epoch fence；
- owner-head revalidation；
- append-only recovery history；
- post-crash Acceptance 与 finality。

**此前未闭合的语义**

- source 必须先唯一完成 exact Target occurrence/readback，再被外部 signal termination；
- crash cut 前 full capsule、Target evidence、owner native heads 和未完成 obligations 必须持久；
- migrated runtime 必须是不同 PID/key/state identity 和更高 epoch，并且只能补 postconditions，
  不能第二次 `EXECUTE`；
- old runtime restart 必须实际 reopen source state、证明 source credential，再被 durable fence
  以 stale epoch 拒绝；
- source history 必须是 migrated history 的逐项前缀；
- O_Q/O_V Acceptance 与 O_P finality 必须从 cut-time owner heads 之后 append；
- removal world 必须保持同一 source prefix，但在 cut 后真正隔离 Target receipt/readback，
  不能只让 cooperative code 假装不看。

**接受结果**

root fresh-run `suite-688917cb80094ed49d5f8e4195a811a8` 支持：

```text
baseline = RECOVERED_AFTER_MIGRATION
migrated accepted EXECUTE count = 0
postcondition count = 3
removal = BOUNDED_UNKNOWN/UNRECONCILED_EFFECT
removal replay/Acceptance/finality = 0/0/0
```

因此，成熟的
`durable history + signed capsule + Target receipt/readback + persistent epoch fence +
owner-head revalidation + post-crash acceptance/finality`
组合已经关闭本地合成、受控 process-termination E6 residual。这仍是“现有技术正确组合”
的正向成果，不需要为保持独占而另造迁移原语。

**非主张与剩余边界**

不证明不可预告物理硬崩溃、物理 Effect、法律 Authority、OS 级 noninterference、恶意同目录
writer、真实跨机 transport、生产长期可靠性、跨实现普遍性或 V1/V2。

### H. E1/E5：本综合不作新判定

当前允许的正式来源闭包没有提供 Wave 014–019 中针对 E1/E5 的独立 case acceptance。因此
本综合不从相邻案例、旧结果或术语相似性推导它们的状态：

`E1/E5 = NOT ASSESSED IN THIS SYNTHESIS`

这不是失败结论，也不是否定历史；只是拒绝用未在本轮来源闭包中重验的材料填补证据空白。

## 六、RAG、ARD、Agent Card 和目录到底解决什么

这里把用户所说的 ARD/Agent Resource Directory 按功能定义为：对 Agent、能力、资源或
endpoint 的描述进行登记、索引、查询和发现的目录型机制；本综合不对任何特定厂商实现作
未核实的产品主张。

| 机制 | 可以正向解决 | 需要已经存在的前提 | 不能单独推出 | 在通爻方案中的合适位置 |
|---|---|---|---|---|
| RAG | 从已收集、可检索材料中找相关上下文，降低已知语料的检索成本 | query、corpus、切分/索引、访问策略、相对稳定的语义映射 | 未表达 Intent、Principal 认领、Mandate、新关系、新条件、current Authority、Effect、Acceptance | 已知关系或已表达候选内的证据检索、上下文补全 |
| ARD/目录 | 把已声明 Agent/资源/endpoint 变成可定位候选 | 主体愿意登记、描述可验证、更新/撤销机制、访问与披露规则 | “应该寻找什么”、未声明能力、真实可用性、合法代表权、commit-time current、任务完成 | 显式候选空间的缩小、路由和 endpoint discovery |
| Agent Card | 以标准描述暴露身份、能力、接口和部分约束 | 发布者身份、声明 schema、版本与真实性来源 | capability 等于 Authority、声明等于现实能力、调用等于授权、输出等于 Effect/Acceptance | candidate qualification、接口协商和兼容性检查 |
| 通用搜索/匹配 | 在表达空间中提高候选召回与排序 | 可比较表示、查询目标、可披露特征 | 新条件形成、权威协调、拒绝处理、事务提交、验收与恢复 | 发现阶段的一个 provider，不是全生命周期 truth owner |

### 1. 动态世界

目录和 RAG 的结果必然对应某个观察时点。世界持续变化时，需要把它们输出视为候选，而不是
commit authorization。执行前还需查询 owner-native current head、revocation、reservation、
capability freshness 和 Target status。Wave 016、018、019 分别给出了 ACK、撤销和
commit-time revalidation 的具体证据。

### 2. 未表达 Intent

没有任何对外信号时，外部系统原则上无法区分：

- 主体没有某个需求；
- 主体有需求但尚未意识到；
- 主体意识到但不愿披露；
- 主体只愿对某类接收者、某种用途披露；
- 主体希望探索，但尚未授权任何行动。

搜索不能凭空消除这种不可识别性。可以研究的是怎样创造更好的表达条件：渐进澄清、局部
提示、可撤回的探测、最小必要披露、匿名/受控表示、recipient-bound 询问，以及明确
`Unknown/REFUSE/DEFER`。

### 3. 披露、隐私与拒绝

创造跨主体可能性需要至少暴露某些可匹配差异；完全零披露与可被他者发现之间存在结构张力。
但这不意味着必须复制完整世界或一次性公开全部上下文。

需要被研究和实现的是：

- 谁可以看到什么；
- 为哪个 purpose；
- 在什么粒度和时限；
- 是否可撤销、过期和不留存；
- 是否允许先询问再披露；
- 拒绝后哪些 descendants 必须归零；
- 披露不足时保持什么类型的 `Unknown`；
- 披露收益是否高于隐私、治理和机会成本。

ARD 或 RAG 可以执行已经确定的披露策略，不能替 Principal 决定策略，也不能把拒绝解释为
检索失败。

### 4. Authority

目录中的“能做”、Agent Card 中的 capability、模型的 plan 和 workflow 的可执行节点都不等于
Principal 的 Mandate。Wave 019 证明，在 E2 的受检验作用域内，Authority closure 需要各
owner 自己的响应、head、scope、expiry、nonce 和 commit-time revalidation；controller 或
broker 不能代签。

### 5. Effect 与 Acceptance

搜索结果、Card、目录命中和模型输出都不是 Target-native occurrence。Wave 014–019 反复要求：

- Target truth store；
- exact operation/Target/Q binding；
- occurrence/readback；
- exact-once；
- owner Acceptance；
- finality。

它们也不证明现实法律或物理世界已经发生同样的 Effect。数字 evidence 与现实 witness 之间仍
需专门桥接。

## 七、把现有技术分成三类，而不是分成“我们的/别人的”

### 1. 已经完整正向解决有界问题

| 结果 | 当前接受范围 |
|---|---|
| E0 平台原生 direct path | `U / LAWFULLY_UNIFIED` 本地合成数字任务 |
| Target-native receipt/readback | Wave 014 相同终态下的直接 actor 归因 |
| SQLite/CAS/one-shot capability/receipt | Wave 015 本地 Target direct attribution、exact-once、并发 residual |

这些都应直接进入候选方案库。若后续现实环境仍满足同一前提，不应为了“原创性”重复发明。

### 2. 单个组件不足，但成熟组合已经正向解决

| 结果 | 已接受的成熟组合 |
|---|---|
| E2 condition formation | workflow + independent HITL owner acts + scoped grant + reservation + commit-time gate + Target/Acceptance evidence |
| E3 ACK-lost pair | Target ledger + exact signed status/readback + freshness + one-shot capability + idempotent retry |
| E4 revoke/alternative | revocation + bounded reopen + compensation + rediscovery + owner receipts + fresh status + durable idempotent ledger |
| E6 controlled process-termination recovery | durable history + signed capsule + Target receipt/readback + persistent epoch fence + owner-head revalidation + post-crash Acceptance/finality |

这类成果说明，通爻的价值可以是：

- 找到此前散落的组件；
- 把它们放到正确的权威和 truth-owner 边界；
- 明确语义、时序、失败和验收合同；
- 形成可复现、可迁移的组合；
- 发现移除哪个组件会重新失败。

它不需要额外制造一个“通爻专属算法”才成立。

### 3. 仍需解题，但尚不能声称必须创新

当前 residual 包括：

- E6 从受控 process termination 走向不可预告物理硬崩溃、真实跨机 transport 与生产恢复；
- 开放世界中表达前的 discovery 与渐进披露；
- 真实法律身份与 Authority 绑定；
- 真实物理 Effect 与现实安全 witness；
- 真人理解、Adoption、Acceptance 与责任；
- provider 停更、格式迁移、许可、锁定、可观察性与恢复；
- 长期漂移、跨域迁移和 RelationEcology 编译/重开；
- 相对 A1–A5 与组合 arms 的真实生命周期净价值。

这些应被标为：

`UNVALIDATED_SOLUTION_RESIDUAL`

而不是：

`CONFIRMED_NOVEL_MECHANISM_REQUIRED`

当前正式接受材料中，后者数量为零。创新的门槛应是：

1. 同一原始任务、Authority stratum、披露边界和成本口径已冻结；
2. 现成标准、平台、制度、人类流程和成熟组合已被公平实现；
3. 失败来自明确、可复现、不可由配置或组合修补的 residual；
4. residual 对原始价值有实质影响；
5. 新机制同时处理功能、失败、迁移、维护、证据和验收，而不是只给一个新概念。

## 八、公平比较尚未运行，不能偷偷补上胜负

Wave 021 当前状态是：

```text
FAIRNESS_CONTRACT = FROZEN_AND_MACHINE_CHECKED
COMPARATIVE_RESULTS = NONE
FINAL_WINNER = NONE
EXISTING_TECH_FULL_SOLUTION = STILL_POSITIVE_AND_OPEN
```

因此，下列说法现在都没有证据：

- Towow/A4 优于强中心、通用模型、真人或成熟组合；
- 强中心能够跨越 `P / PLURAL_INDEPENDENT` 的 owner Authority；
- 通用模型能够把输出当成 Authority、Effect 或 Acceptance；
- 人类一定更慢或更贵；
- 已接受的 E0/E2/E3/E4 可直接记为某个 arm 的横向胜场；
- 某个方案具有最低全生命周期成本。

公平比较必须保持：

- 同一 Q、Target、deadline、Effect、Acceptance 和 finality；
- 同一 public view、owner/Target API、预算、披露和故障语义；
- 语义 `arm_id` 不进入 arm view；
- 故障按 native semantic boundary，而不是 raw ordinal、wall time 或 trace hash；
- `Unknown`、refusal、`NOT_APPLICABLE` 与 failure 分开；
- Authority stratum 内比较，不选跨 stratum 总冠军。

这也是“为什么以前没有解决”的另一部分答案：若没有同任务、同信息、同权威和同验收合同，
不同方案的成功无法区分真实能力与额外 oracle、额外重试、额外披露或目标缩小。

## 九、对下一轮研究策略的直接改变

### 1. 先写完整任务，再选技术

每个候选技术进入方案前，必须先明确：

- 环境和 Authority stratum；
- 已有输入与哪些对象尚未表达；
- 原始 Q、V0、Target、deadline 和不可接受底线；
- owner topology、披露策略和拒绝权；
- 动态失败、撤销、ACK、crash 和漂移位置；
- Target、Effect、Acceptance、finality 的 truth owner；
- success、bounded refusal、Unknown、reopen 和 removal world。

然后再判断 RAG、目录、Card、workflow、IAM、中心、人类、模型或组合分别承担哪一段。

### 2. 把成熟组件视为能力库，不视为竞争阵营

平台、中心、通用模型、人工制度、RAG、目录、Agent Card、事务、ledger、HITL、saga 和
fence 都是可路由组件。稳定路径应尽量编译；开放形成只处理尚未被编译的差异；漂移后只重开
真实受影响部分。

### 3. 下一项最高信息增益不是再论证“通爻是否特别”

下一步应优先：

1. 把已接受的 E6 local-synthetic 组合压力推向不可预告硬崩溃、真实跨机 transport 和恢复；
2. 在 Wave 021 包络内实际运行 A1/A2/A3/A5 及预注册组合；
3. 把一个 local-digital accepted case 桥接到真实 Authority、物理 Effect 或真人
   Acceptance，测量哪里首次失真；
4. 对 RAG/ARD/Card 做有界实验：它们提高了哪一类显式候选的召回，在哪些未表达 Intent、
   stale Authority 和 disclosure refusal 条件下必然停住；
5. 记录真实生命周期成本，检验组合是在减少 material judgment，还是把它转移到接入与治理。

## 十、证据绑定与非主张账本

| 来源 | 文件 SHA-256 | 本综合使用的正式结论 | 不能从中推出 |
|---|---|---|---|
| Problem V2 JSON | `cb6d4bd9c5930181df9176957daa144085a3eaf9f1edfc3c3992cd87f94a2f46` | V2 为 ACTIVE；V1 加法继承；开放行动世界、Authority 不可静默代行、三尺度与强基线 | 任何具体机制已经有效 |
| Problem V2 Markdown | `d305867ca07d02f86daddfe8bb76fc22df5a68ee18edb7ce599e6c03a2ab3cc8` | Intent 到达不等于认领/授权；中心/平台/人类是正向基线；Capability 到 Settlement 可分别失败 | 上游隐式 Intent 已被解决 |
| V1 candidate JSON | `9a59de81ac7c5ca0a42ff012bbade98b4be60978742b3c81d26f9024a3e9b408` | 冻结 S0/Q/V0/Principal/Authority/Target/基线；发现、条件创造、问题改写分开 | V1 为独立 ACTIVE 快照 |
| V1 candidate Markdown | `7982aa908ce4e457e655fbe553db228f2ab9a09fdaa1202309df261d1bdc4a56` | RAG 只能降低已知语料检索成本；不能自动形成未知角色、局部权威、新条件、现实 witness 与接受规则 | 通爻已经降低生命周期成本 |
| Wave 014 root acceptance | `8f3532834d5808ee0679765ee07e68586add725f88f7f94b8453434db123eba8` | Target receipt/readback 区分相同终态下的直接 actor | 法律 Authority、物理 Effect、V1/V2 |
| Wave 015 root acceptance | `b54d52e39a2b5f6b124dd24d8a33f0f6b7c22413b3d8150a823f14c7724e43ca` | 成熟 Target ledger residual 已关闭；runner foundation 可组合 | E3/E4/E6 或 CE-001 完成 |
| Wave 016 root acceptance | `dc6b123b89b6be72ee28c9d34e3f360d09f940f615bbe4f09c66433e1ae693b8` | 成熟组合关闭本地数字 E3A/E3B ACK-lost pair | 法律、物理、生产、formation |
| Wave 017 root acceptance | `f05623c0d42293e9d3c6f5feb7175a61ad88abf22b2da039ab259b54a82968e3` | 合法统一平台直接完整解决 E0 有界任务 | P、多主体协调、CE-001 全 family |
| Wave 018 root acceptance | `4250e513588551cc17a0bb2a812fc24309dbaa13829c1b4ab92827cbcbd92a17` | 成熟组合关闭本地合成 E4；移除 alternative 得 bounded refusal | 现实法律/物理、人类接受、provider 生命周期 |
| Wave 019 root acceptance | `e5963e5fe0dda960f77f7d0b1416d864a0a745e0e5aae1aa94f693e4d0093c3` | 成熟 workflow/HITL/scoped grant/reservation/gate 关闭本地 E2 | 法律 Authority、物理 Effect、跨域/净价值 |
| Wave 020 root acceptance file | `731e017e3301863c3a4924601fd8b4dfec6991118fd57d04a88fedc7e3017e0b` | 成熟 durable recovery 组合关闭受控 process-termination 的本地合成 E6 | 不可预告硬崩溃、物理/法律、真实跨机、生产与 V1/V2 |
| Wave 020 independent red-team | `c00c7eb745e4a9411587ab365d6eb110a428652051561a9abe27061265b2ef42` | 保存九类原始阻断、两类后续 oracle/评估缺陷、root fresh-run、25 attacks 与 scoped acceptance 边界 | 独立现实部署或跨实现复现 |
| Wave 021 audit | `f1afc13a488bfe319f7276bf1bcbeb1877c2d7cd7dcf45b15064cf30cfe10d9d` | 公平合同已冻结；比较运行数为 0；winner 为 none | 任一 arm 优胜 |
| Wave 021 contract file | `91a0e174971782362672e0909240b7f2467d68969a103542282e92c90297a41d` | 同任务、同 view、同 owner/Target API、同失败语义和多维结果向量 | 合同充分性或现实外部有效性 |

Wave 021 合同自身登记的 canonical content hash 为：

`8fe94be48d8d2bc506af292ac6b0015160d8d2eaab059c619e930ce0f77f8362`

## 十一、最终研究判断

“已有技术为什么没有解决我们的问题”不能用一句“因为它们都不够先进”回答。当前证据给出的
更精确答案是：

1. 它们中的许多已经完整解决了被预编译、已表达、单一权威域内的问题；
2. 它们往往把开放关系中最难的角色、语义、Authority、披露、验收和例外判断留给平台设计者
   或高语境人类；
3. 动态故障发生在组件、owner 和时间边界之间，单个功能的存在不能闭合整条行动链；
4. 一旦把 exact task、owner topology、时序、truth owner、failure 和 Acceptance 明确下来，
   E0/E2/E3/E4/E6 以及两个 Target residual 已被现有成熟技术直接或组合解决；
5. 这已经是通爻的实质成果：不是证明自己独占，而是找到可复现、可复用、可迁移的解法；
6. 剩余问题必须继续解决，但在成熟组合尚未接受同条件检验之前，不能偷跑到“必须创新”；
7. 若后续确实定位出无法由成熟方案覆盖的有界 residual，创新必须完整承担功能、失败、迁移、
   维护、证据与验收，而不是只创造一个新名称。

目前最诚实、也最建设性的总状态是：

```text
MATURE_PRIMITIVES_EXIST = TRUE
SCOPED_DIRECT_SOLUTIONS_EXIST = TRUE
SCOPED_EXISTING_COMPOSITIONS_SOLVE_MULTIPLE_CASES = TRUE
FAIR_CROSS_ARM_COMPARISON_RUN = FALSE
E6_LOCAL_SYNTHETIC_CONTROLLED_TERMINATION_CLOSURE = ACCEPTED_SCOPED
E6_UNANNOUNCED_HARD_CRASH_CROSS_MACHINE_PRODUCTION = UNKNOWN
CONFIRMED_NOVEL_MECHANISM_REQUIRED = NONE
V1_V2_OVERALL_SOLVED = FALSE
```
