# G4 ChatGPT Pro return

- Conversation: https://chatgpt.com/c/6a69e1d0-dadc-83ea-a0db-28f41051b572
- Captured: 2026-07-29
- Status: external candidate evidence; not independently validated
- Preservation note: assistant visible text transcribed verbatim from the signed-in in-app browser; page structure and link previews are not embedded here.

---

G4 独立重建报告：从能力证据到可依赖行动

研究日期：2026 年 7 月 29 日

一、结论先行

我的独立判断是：

G4 在大多数单组织、强治理或可联邦化环境中，首先是一个成熟工程组合问题，而不是一个必须发明新协议的问题。

目前最强的无新协议方案，是把以下能力连成一条不可跳步的执行链：

不可变版本绑定
→ authoritative current read
→ exact-operation Authority 与实时授权
→ 关键依赖 reservation/lease/fencing
→ 同一事务内重验与写入执行意图
→ outbox/幂等执行/持久工作流
→ 有界重试与拒绝语义
→ authoritative readback
→ 接受、已知失败或明确的 unresolved 终态

它不是把八个绿色字段打包成一张“可靠性证书”，而是把其中一部分观察性证据转化为受目标系统承认的短期约束或承诺。

但原问题里确实存在一个不能被成熟栈、强中心、通用模型或多 Agent 投票消除的边界：

当两个世界向决策者暴露完全相同的 packet 和相同的可查询结果，但某个隐藏 Authority、依赖或物理状态使真值相反时，任何算法都不可能同时做到零 unsafe false reliance 和满 safe recall。

它若声称做到了，必然发生了三件事之一：

偷渡了额外 oracle；

实际上取得了更强的 Authority 或可观测性；

改写了“可依赖”的含义。

因此，G4 真正剩余的研究对象不是“如何更聪明地判断 capability”，而是：

在独立、可拒绝、可撤销、部分不可查询的 Authority 边界上，怎样以有限披露和有限时延取得足以支撑下游承诺的临时约束，并在执行结果不明时获得 authoritative resolution。

这可能需要创新，但创新对象应是新的信息或约束原语，例如低披露当前态查询、绑定 exact operation 的短期承诺、目标端实际执行的 fencing、跨域结果回执。仅仅重命名 readiness、生成一个 LLM 置信分、让多个观察者投票，均不构成新证据。

二、原问题可能问错了什么
2.1 “可依赖”不是主体或服务的固有属性

原问题容易被写成：

Agent A 是否具备并能执行 operation O？

正确对象应当是：

某个主体是否可以在特定时间窗、风险预算和失败语义下，对一个完整绑定的操作实例作出下游承诺？

这个操作实例至少应包含：

X = {
  requesting_principal,
  acting_identity,
  authority_basis,
  operation_id,
  implementation_digest,
  API_or_schema_version,
  arguments_hash,
  target_identity,
  critical_dependencies,
  dependency_currentness_policy,
  deadline,
  idempotency_key,
  allowed_terminal_states,
  authoritative_readback_source,
  recovery_policy,
  acceptance_rule
}

只写 operation/version 仍然不够。两个调用即使 operation 名和版本相同，只要参数、目标、Authority、依赖集合、截止时间或接受规则不同，就是两个不同的依赖命题。

2.2 “现在可用”不是一个瞬时判断

至少存在五个时点：

t_observe   证据产生
t_decide    系统决定依赖
t_commit    下游据此作出承诺
t_execute   目标真正执行
t_accept    结果被 authoritative principal 接受

健康、授权和 attestation 在 t_observe 成立，不意味着在 t_execute 仍成立。RFC 9334 对 attestation freshness 的讨论明确指出：即使有时间戳、nonce 和过期策略，设备状态或评价策略仍可能在结果生成后立即变化，因此始终存在竞态；freshness 只能把竞态窗口缩小，不能消灭。
RFC 编辑器

所以，真正有用的不是“刚刚查过”，而是以下二者之一：

check 与 act 在同一原子域中完成；

检查后获得了在操作窗口内受目标端承认的 lease、reservation、fencing token 或 binding commitment。

2.3 “判断”与“使其变得可依赖”被混在了一起

查询 readiness 是观察世界。

取得资源 reservation、获得双人批准、锁定版本、写入幂等意图、取得目标系统认可的 fencing token，则是在改变世界。

可依赖性经常不是被更准确地“发现”的，而是在决策过程中被部分构造出来的：

不确定是否可执行
→ 查询当前态
→ 请求 Authority
→ 锁定资源和版本
→ 形成短期承诺
→ 原子重验
→ 执行

这正是为什么单靠 capability packet 不够。

2.4 “成功保证”与“可依赖的结果契约”需要区分

强定义是：

exact operation 一定在截止时间前成功。

在存在故障和持续拒绝权时，这通常不可成立。

更现实、也更接近成熟系统所能提供的定义是：

截止时间前一定到达一个 authoritative terminal state，例如
SUCCEEDED、REFUSED_NO_EFFECT、FAILED_NO_EFFECT 或 FAILED_COMPENSATED，且不会遗留未被识别的副作用。

也就是说，真正可依赖的首先是结果可决性，其次才是成功概率。

Google SRE 明确把可靠性作为风险预算和目标水平问题，而不是默认追求所有服务 100% 成功；这与对单次 exact operation 使用有界失败契约而非绝对成功承诺是一致的。
Google SRE
+1

2.5 “不无限弃权”不是要求系统冒险猜测

它要求的是一个有界的三动作策略：

COMMIT / RELY
QUERY / ESCALATE
DECLINE / ABSTAIN

QUERY 只能是中间态。系统必须具有：

最大查询次数；

最大等待时间；

人工升级窗口；

到期后的明确终态；

对 REFUSED、UNKNOWN、STALE、REVOKED 的不同处理。

到期后输出 UNRESOLVED_DECLINE 是有界弃权；一直显示“仍在判断”才是无限弃权。

三、可依赖性的正确判据

可以把 exact operation 的可依赖性写成以下证明义务：

RELYABLE(X, t0, Δ, ε) =
    SEMANTICS_BOUND
  ∧ LEGITIMATE_AUTHORITY
  ∧ LIVE_AUTHORIZATION
  ∧ CURRENTNESS_POLICY_SATISFIED
  ∧ COMMITMENT_CLOSURE
  ∧ SAFE_EXECUTION_SEMANTICS
  ∧ AUTHORITATIVE_OUTCOME_RESOLUTION
  ∧ RESIDUAL_RISK ≤ ε

各项含义如下。

1. SEMANTICS_BOUND

操作、实现 digest、参数、目标、依赖版本和接受规则均已绑定。

Kubernetes 官方文档明确区分可移动 tag 与不可变 digest：digest 可以锁定实际运行代码，而 tag 发生变化时，不同 Pod 可能运行不同版本。
Kubernetes

2. LEGITIMATE_AUTHORITY

作出批准的主体在组织、法律、业务或物理制度上确实有权约束该效果。

它不等同于“拥有一个能调用接口的 token”。

3. LIVE_AUTHORIZATION

在实际使用时，调用身份仍被访问控制策略允许。

OAuth token introspection 可以查询 token 是否“当前 active”，但真实 IAM 系统常存在变更传播延迟；AWS IAM 官方文档明确要求应用考虑 eventual consistency。
RFC 编辑器
+1

4. CURRENTNESS_POLICY_SATISFIED

不是机械地要求 version == current HEAD，而是满足该依赖的版本政策，例如：

EXACT_DIGEST_ALLOWED
CURRENT_APPROVED_HEAD_REQUIRED
MINIMUM_VERSION
COMPATIBILITY_RANGE
NOT_REVOKED

Git branch/ref 本身就是可被重写到新 commit 的指针；“精确版本”与“当前 head”是两个不同命题。
GitHub Docs

5. COMMITMENT_CLOSURE

对每个关键依赖，至少满足以下之一：

它与操作在同一原子事务或同一强控制域内；

它提供在执行时间窗内有效、受目标端执行的 reservation/lease/fence；

它失败时有已被下游接受的替代路径，因而不再是关键依赖。

只有“查到绿色”而没有闭合约束，不构成 commitment closure。

6. SAFE_EXECUTION_SEMANTICS

包括：

idempotency key；

duplicate suppression；

bounded retries；

fencing；

超时后不把 UNKNOWN 当作 FAILED；

compensation 本身作为新的、有 Authority 的操作处理。

7. AUTHORITATIVE_OUTCOME_RESOLUTION

执行后存在一个有权决定事实状态的 readback 来源。

网络 ACK 不是 authoritative readback。ACK 丢失可能对应“操作已执行”和“操作未执行”两个世界。AWS 关于幂等 API 的工程说明就以创建实例响应超时为例：调用者无法知道工作负载是否已启动，直接重试可能制造第二个实例，因此必须执行 reconciliation。
Amazon Web Services, Inc.

8. RESIDUAL_RISK ≤ ε

历史成功、SLO、健康、模型判断和人工经验主要作用于这里：它们估计剩余风险，而不是自动满足前七项。

四、八类信号各自证明什么
信号	它真正证明的内容	它不证明的内容
capability 声明	某接口、工具或实现声称支持某类操作	当前部署、当前版本、权限、资源、意愿、成功或结果可回读
历史成功	过去分布中的统计表现	本次 exact operation 的当前真值
readiness/health	某个探针当前给出可服务状态	全依赖闭合、足够容量、Authority、未来不拒绝
permission/IAM	某身份按某策略可以发起请求	该请求具有业务上的正当 Authority，或目标一定接受
reservation	某资源在某范围和期限内被保留	主体承诺执行、外部资源承认 reservation、执行成功
dependency current-head	所观察到的版本头满足某种新鲜度关系	该 head 语义兼容、未被回滚、exact pinned 版本必须等于 head
recovery	有故障处理或补偿路径	初次操作是否发生、补偿是否成功、最终状态是否已知
Authority	某主体有权批准或拒绝	当前 readiness、资源、权限或实际执行
attestation	某 verifier 根据证据和策略对设备状态作出评价	将来的行为、业务意愿或 exact operation 的成功

OpenAPI 的职责是描述可用 operation 和输入输出；gRPC health 则明确由服务实现者负责更新 SERVING/NOT_SERVING 状态。这两个标准本身都没有把声明或健康提升为未来执行承诺。
OpenAPI Initiative Publications
+1

服务发现结果还可能为了可用性和延迟而有意允许陈旧。例如 Consul DNS 服务发现当前默认通过 stale consistency mode 查询底层 catalog/health；需要更强一致性时必须显式选择更昂贵的查询路径。
Consul | HashiCorp Developer

reservation 也不能靠名字获得强度。etcd 官方说明非常直接：lease 本身并不保证互斥；要保护 etcd 外部资源，外部资源也必须实现相应的版本校验或 fencing，etcd 的 lock 不能单独保护外部对象。
etcd

五、动态状态不能被压成一个“不可用”
状态	正确语义	默认动作
UNKNOWN	没有足够信息判断；不等于失败	在预算内查询或升级；到期后 unresolved decline
REFUSED	Authority 有意拒绝披露、批准或执行	停止自动重试；除非收到新的邀请或条件改变
STALE	已知证据不再满足 freshness/currentness	刷新证据或重新取得 commitment
REVOKED	先前授权、版本认可或 reservation 已被撤销	使所有依赖该依据的未执行承诺失效
COMMIT_READY_UNTIL τ	exact operation 已获当前授权、Authority 和关键依赖约束	必须在 τ 前原子提交，否则重新检查
EXECUTED_UNCONFIRMED	请求可能已产生副作用，但无 authoritative result	禁止盲目重试或补偿，先 readback
ACCEPTED	authoritative principal 已接受 postcondition	才能向上游报告完整完成
UNRESOLVED	到期仍不能确定权威终态	进入业务应急或人工 reconciliation，而不是伪装失败

最重要的一点是：

REFUSED 是权利的行使，不是暂时性故障。

把 REFUSED 和超时都放进指数退避重试，会把“尊重拒绝权”退化成“持续骚扰，直到成功”。

同样，如果主体拥有一直延续到执行前最后一刻的绝对拒绝权，那么外部系统不可能承诺“操作一定成功”。它最多能够依赖：

主体将在截止时间前执行，或给出 authoritative refusal/no-effect。

要取得成功级承诺，主体必须自愿把拒绝权在一个限定窗口中转化为 binding commitment，或者下游必须接受失败分支。

六、最强成熟组合：无新协议基线

以下是我认为必须先被实现和击败的 Mature Composite Baseline，MCB。

6.1 先定义依赖契约，而不是先搜 capability

必须先声明本次依赖的是哪一种保证：

A. SUCCESS_BY_DEADLINE
B. STARTED_BY_DEADLINE
C. EXACTLY_ONCE_OR_NO_EFFECT
D. AUTHORITATIVE_TERMINAL_STATE_BY_DEADLINE
E. BEST_EFFORT_WITH_SLO

其中 D 通常是最实际的生产级默认值。

6.2 绑定不可变操作实例

绑定：

实现 digest；

API/schema version；

参数 hash；

target identity；

dependency set；

Authority basis；

idempotency key；

acceptance rule。

版本名、branch、tag 可以作为发现入口，但不能作为最终执行身份。

6.3 对关键状态进行 authoritative current read

需要 current 的状态应使用明确的一致性级别，而不是默认缓存。

etcd 默认线性化读取反映集群当前共识，事务可以基于 revision 做 compare-and-swap；Kubernetes API 也提供与资源版本相关的一致读取和乐观并发控制。
Kubernetes
+3
etcd
+3
etcd
+3

这里要注意两个成本：

强一致读增加延迟和控制面负担；

所有状态都做强一致读会降低可用性并造成查询风暴。

因此只对真正会改变承诺真值的关键依赖使用 authoritative read，其余状态留在 SLO 风险模型中。

6.4 在使用点验证身份、授权和 Authority

技术授权应做到：

短生命周期；

exact audience；

exact scope；

使用点 introspection 或等价新鲜度控制；

与 workload identity 绑定。

SPIFFE Workload API 使用流式更新帮助传播身份材料变化和撤销，并鼓励使用短期证书；这降低了长期凭据风险，但仍不能创造业务 Authority。
SPIFFE
+1

业务 Authority 应绑定：

operation_hash
principal
scope
expiry
revocation_terms
approval_count

高风险操作可以直接使用成熟的 dual authorization。NIST 将其定义为至少两个获授权人员共同执行、且双方都能发现错误或未授权程序的控制机制。
NIST计算机安全资源中心

6.5 对关键依赖取得受目标端执行的 reservation/fence

reservation 必须回答：

保留了什么？
为哪个 exact operation？
由哪个 Authority 发放？
有效到何时？
是否可以撤销？
目标端如何拒绝过期或旧 token？

如果 reservation 仅存在于协调器数据库，而实际资源不验证 fencing token，那么它只是愿望记录。

6.6 原子地“重验并提交执行意图”

在同一事务或 CAS 中完成：

检查 version/head predicate
检查 Authority 与授权仍有效
检查 reservation/fence
写入 operation intent
分配唯一 idempotency key
写入 outbox event

PostgreSQL 等数据库的 serializable transaction 可以在单一数据库范围内阻止序列化异常；发生冲突时应用必须重试整个事务。
PostgreSQL
+1

Outbox 模式可以把业务状态更新与待发布事件放进同一数据库事务，避免经典 dual-write 不一致；但跨服务传播仍是 eventual，并不自动让外部操作 exactly-once。
Debezium
+1

6.7 使用持久工作流，但不把工作流当作成功 oracle

Temporal 一类 durable workflow 能保存状态、重放、超时和重试，但其 Activity 可能以 at-least-once 方式执行，因此官方实践仍要求外部调用使用 idempotency key、check-before-act 和 upsert。
Temporal 文档
+1

所以：

durable workflow ≠ durable truth
retry ≠ recovery
compensation ≠ rollback

工作流保证协调过程不轻易丢失，不保证每个外部副作用只有一次，也不保证外部 Authority 接受。

6.8 超时后先 readback，再决定重试

执行 API 应至少提供：

submit(operation_id, idempotency_key)
read_status(operation_id)

若 read_status 不存在，exactly-once 或 authoritative recovery 的主张通常无法成立。

Debezium 的官方连接器文档也明确说明，故障后从已记录位置恢复仍可能重新产生重复事件。这正说明日志恢复和“业务效果只发生一次”不是同一个命题。
Debezium

6.9 attestation 和 SRE 作为风险控制，而不是承诺替代品

RATS 把 Evidence、Verifier、Attestation Result 和 Relying Party policy 明确分开：最终是否允许操作仍由 relying party 的应用策略决定。
RFC 编辑器

SRE 解决的是：

aggregate reliability；

overload；

error budgets；

cascading failures；

retry budgets；

incident recovery。

它不能为单个 exact operation 提供逻辑必然性。过度重试本身还可能放大级联故障，因此成熟 SRE 会限制单请求重试次数。
Google SRE
+1

6.10 一个不依赖新协议的决策算法
evaluate(X):

  1. bind exact operation, digest, args, target, deadline
  2. identify critical dependencies and currentness policy

  3. for each critical dependency D:
       state = authoritative_query(D)

       if state == REFUSED:
           return DECLINE_REFUSED

       if state == REVOKED:
           invalidate dependent approvals/reservations
           return DECLINE_REVOKED

       if state == STALE:
           refresh within query/time budget
           otherwise return DECLINE_STALE

       if state in {UNKNOWN, DECLARED_UNQUERYABLE}:
           try to obtain a binding commitment/reservation
           if unavailable:
               apply explicit risk policy
               otherwise return DECLINE_UNRESOLVED

  4. validate exact-operation Authority and live authorization
  5. acquire reservations and fencing tokens
  6. atomically revalidate heads/auth/reservations and write intent+outbox
  7. execute with idempotency and bounded retries
  8. if response is ambiguous:
       authoritative readback before any new mutation
  9. return ACCEPTED / KNOWN_NO_EFFECT / KNOWN_COMPENSATED / UNRESOLVED

这已经可以覆盖大量真实系统，不需要先设计一个跨 Agent 新协议。

七、四类方案的独立比较
方案	最强之处	根本边界	最适用场景
成熟技术组合	可组合 current read、IAM、事务、outbox、workflow、fencing、readback	配置复杂；跨独立 Authority 时常缺少 binding commitment	企业内部、云服务、可改造的 B2B 联邦
同等权限强中心	全局状态机、统一查询和 reservation、易于原子化	同权限下不能看见不可查询状态，也不能代替主体 Authority	单组织或中心确实控制关键资源
通用模型	解释自然语言、规划查询、发现异常、处理长尾	非确定性；不能创造 Authority、当前真值或 fencing	proposal、query planning、异常解释、人工辅助
人工制度	能形成真实授权、承担责任、处理例外和拒绝	慢、昂贵、会疲劳和误判，难以高频扩展	高价值、低频、不可逆、制度性任务
技术＋人工混合	技术闭合状态，人工提供 Authority 和例外判断	仍需设计清楚谁能看什么、谁能承诺什么	当前最强现实方案
7.1 同等权限强中心必须是首要基线

这里必须严格区分两个中心：

超权限中心

如果中心拥有所有局部世界、所有 Authority，并能覆盖主体拒绝权，那么它已经改变了原问题。

此时它当然可能用一个 serializable database、全局调度器和统一 IAM 解决问题，但这不是对原条件的解答。

同等权限中心

正确基线应满足：

与其他方案拥有相同查询 API；

相同 freshness；

相同 rate limit；

相同披露预算；

相同 Authority；

不允许后台直接读取隐藏 oracle；

不允许绕过主体 REFUSED。

这种中心的优势是降低协调复杂度、统一状态机和减少重复查询。它不能克服不可观测性或独立 Authority。

在闭合世界里，它很可能是最强、最便宜的方案。候选创新若无法在安全—召回—成本的 Pareto 前沿上超过它，就没有创新必要。

7.2 通用模型不应担任最终 commit oracle

通用模型适合：

解析 operation 与政策；

推断应查询哪些关键依赖；

生成候选恢复路径；

识别 packet 内部矛盾；

将异常升级给人。

但最终 commit gate 应由可审计的确定性规则、权威查询和受目标端执行的约束完成。

工具 Agent 的现实评测也说明，任务完成能力和可靠弃权不是同一个能力。τ-bench 在其特定客户服务任务中发现当时的强 function-calling agents 单次成功率仍低于 50%，多次一致成功率进一步下降；2026 年的 Agentic Abstention 研究则发现，有些 Agent 应弃权时不弃权，有些在大量无效交互后才弃权。
arXiv
+1

2026 年 7 月的一项预印本 AgentAbstain 使用 act/abstain 配对任务评测 17 个模型和 4 种 harness，报告其最佳 paired accuracy 为 59.5%，并观察到弃权能力与一般任务解决能力相当独立。这个结果是任务特定且尚不足以代表所有生产系统，但它有力支持了“不能把更强模型自动等同于更安全 commit policy”。
arXiv

更重要的是，即使未来模型在这些基准上接近完美，它仍无法突破 packet-identical 的不可区分性。

7.3 人工制度不是落后替代物

在高风险物理任务中，成熟人工制度已经同时组合了：

Authority；

独立复核；

对 exact task 的许可；

物理 reservation；

当前态验证；

主体拒绝；

现场 readback。

例如 OSHA 的 lockout/tagout 制度要求工作许可标识具体设备、危险能源和操作程序；授权人员还需验证能源已隔离，复杂场景中甚至要求持续验证，不能仅依赖早先状态。
职业安全卫生管理局
+3
职业安全卫生管理局
+3
职业安全卫生管理局
+3

这实际上已经是一个很强的 G4 解法，只是吞吐量和自动化程度低。

HITL 也不能被当作免费 oracle。人的判断会受界面顺序、锚定和 automation bias 影响；研究显示仅让人点击“确认/修改”可能增加对先前 AI 判断的顺从。
数字对象标识符

所以人工应拥有真实 Authority、独立信息和拒绝能力，而不是替自动系统做最后一次形式化点击。

八、统一评估指标

设系统对第 i 个任务的最终决策为：

d_i ∈ {RELY, ABSTAIN, DECLINE}

QUERY 和 ESCALATE 是中间动作，不允许成为无限终态。

ground truth 为：

y_i = SAFE

当且仅当 exact operation 的预注册依赖契约在真实状态下可被履行，包括 Authority、版本、关键依赖、执行语义和 authoritative resolution。

对强依赖定义，EXECUTED_UNCONFIRMED 和到期仍无法确定的 UNKNOWN 均应计入 unsafe。

8.1 Unsafe False Reliance
UFR_conditional =
  count(RELY ∧ UNSAFE)
  / count(RELY)

它表示：系统一旦告诉下游“可以依赖”，其中有多少其实不安全。

同时报告：

UFR_all =
  count(RELY ∧ UNSAFE)
  / count(all tasks)

避免一个系统通过几乎全部弃权获得表面上的低风险。

8.2 Safe Recall
Safe Recall =
  count(RELY ∧ SAFE)
  / count(SAFE)

衡量系统没有错过多少真正可以安全兑现的机会。

8.3 Abstention

至少报告：

Abstention Rate
Unnecessary Abstention = ABSTAIN ∧ SAFE / SAFE
Timely Abstention
Queries after infeasibility became observable

“最终弃权正确”不够。如果系统在发现不可行后又进行了二十次泄露性查询，其行为仍然很差。

8.4 查询、披露和时延成本

不建议过早压成一个分数，应先报告向量：

C_query = (
  total_round_trips,
  authoritative_reads,
  query_failures,
  bytes_disclosed,
  sensitivity_weight,
  human_interruptions,
  infrastructure_load,
  monetary_cost
)

T = (
  decision_latency_p50/p95/p99,
  commit_to_terminal_latency,
  recovery_resolution_latency
)

如需综合分数，权重必须在测试前注册，不能在结果出来后调整。

8.5 Authoritative Recovery Readback
ARR =
  ambiguous executions that received authoritative readback
  before retry/compensation
  /
  all ambiguous executions

同时报告：

Blind Retry Rate
Wrong Compensation Rate
Duplicate Side-Effect Rate
Unresolved-at-Deadline Rate
8.6 Authority 安全指标
Unauthorized Commit Rate
Commit-after-Refusal Rate
Commit-after-Revocation Rate
Authority-Scope Mismatch Rate

这些应当单列，不能被总体成功率平均掉。

九、三个真实任务定义
9.1 任务 A：生产环境精确版本发布
Exact operation
Deploy(
  service = payments-api,
  image = registry/payments@sha256:D,
  config_revision = C57,
  database_migration = M42,
  target = prod-us-cluster / namespace payments,
  replicas = 6,
  approval_hash = A,
  deadline = 600 seconds
)
可依赖契约

600 秒内必须到达以下 authoritative terminal state 之一：

1. ACCEPTED:
   6 个有效 replica 均运行 digest D；
   migration M42 只执行一次；
   流量已切换；
   synthetic purchase 成功。

2. KNOWN_ROLLBACK:
   所有新 replica 已隔离；
   旧 digest 已恢复；
   migration 状态和数据兼容性已确认。

3. KNOWN_NO_EFFECT:
   发布在产生外部效果前被拒绝。

如果下游要求“一定上线 D”，则 2 和 3 是已知失败；如果下游只要求“系统不会进入未知混合状态”，则三者都可以满足 bounded-outcome reliance。

Unsafe false reliance

以下任一情况发生却仍输出 RELY：

发布批准已撤销；

IAM 变更尚未传播；

admission policy head 已变化且旧版本被禁止；

使用 mutable tag 导致混合代码；

仅查到 readiness，但容量没有 reservation；

migration 成功后 ACK 丢失，工作流重复执行；

控制器缓存落后于刚写入的 resource version；

rollback 发生但被报告为成功上线；

最终运行 digest 无 authoritative readback。

Kubernetes 近年的一致性改进专门处理 controller cache 落后于已写入 resource version 的问题，这本身说明“控制器缓存里看见绿色”不能自然等同于 current truth。
Kubernetes

查询与披露成本

Git/ref 或制品仓库 current-head；

digest 和签名；

IAM introspection；

admission policy revision；

Kubernetes current read；

capacity claim；

DB migration ledger；

dependency health；

发布批准状态。

披露成本主要是配置、拓扑、镜像元数据和生产状态。

Authoritative readback

至少组合：

Kubernetes most-recent API read
+ actual Pod image IDs
+ rollout ownership/resourceVersion
+ migration ledger
+ service synthetic transaction

只看 Deployment 的“Available”字段不够证明业务 postcondition。

9.2 任务 B：精确金额退款
Exact operation
Refund(
  charge_id = CH-91827,
  amount = 127.43 USD,
  destination = original_payment_method,
  reason = duplicate_charge,
  processor_operation_version = V,
  merchant_principal = P,
  idempotency_key = K,
  deadline = 300 seconds
)
可依赖契约

300 秒内必须 authoritative 地确定：

REFUNDED_EXACTLY_ONCE
DECLINED_NO_EFFECT
FAILED_NO_EFFECT

不能接受：

可能已退，也可能未退
可能退了一次，也可能两次
内部账本显示已退，但支付处理方无记录
Unsafe false reliance

商户 Authority 已撤销；

当前 charge 已由其他流程退款；

可退款余额低于 127.43；

token technically active，但不具备本次业务 Authority；

processor 已处理请求但响应丢失，系统换新 idempotency key 重试；

outbox 发布成功但内部账本事务回滚；

内部账本成功，外部处理方拒绝；

recovery 直接做反向补偿，却不知道初次退款是否发生。

查询与披露成本

charge 当前状态；

剩余可退款金额；

fraud/legal hold；

merchant Authority；

双人批准；

processor 当前 API contract；

processor transaction status。

这些查询可能披露客户交易和风控信息，因此不能把“多查一次”视为免费。

Authoritative readback

至少需要：

processor-side transaction record keyed by K
+ merchant ledger entry
+ reconciliation relation between both

如果处理方拒绝提供状态查询，并且也不提供幂等回执，那么系统无法证明 exactly-once；最多能承诺“已提交请求”。

9.3 任务 C：制造设备执行精确工艺程序
Exact operation
RunBatch(
  machine = CNC-M17,
  program_digest = P,
  approved_recipe_head = R,
  fixture = F3,
  material_lot = L219,
  quantity = 100,
  operator = O,
  safety_permit = S,
  quality_plan = Q,
  deadline = end_of_shift
)
可依赖契约

必须满足：

程序 digest 精确；
recipe policy 允许 P；
设备、夹具、刀具和材料已保留；
无生效中的维护锁或人员 LOTO；
操作者和安全主体具有 Authority；
开始最多一次；
最终有 accepted count、known no-start 或 known safe-stop；
不能留下是否已经转动、加工多少件均不明的状态。
Unsafe false reliance

MES 显示 ready，但现场维护人员仍持有个人锁；

设备控制器程序已更新，MES 仍缓存旧 digest；

操作者拒绝，但调度器把 reservation 当成 consent；

刀具寿命或材料批次状态 stale；

控制网络中断后，调度器不知道程序是否开始，重新下发；

PLC cycle count 与 MES 工单状态冲突；

机器完成加工，但 QA Authority 未接受成品。

查询与披露成本

设备状态和 interlock；

LOTO/maintenance 状态；

程序与 recipe digest；

人员身份和班次；

材料、刀具和夹具；

生产计划和工艺参数。

这些数据通常包含企业敏感工艺信息，说明开放协作里的 current query 与隐私确实存在真实张力。

Authoritative readback

应预先规定事实来源：

物理执行事实：PLC/设备控制器的受保护事件记录
业务完成事实：MES operation record
质量接受事实：QA acceptance record

三者不同。设备执行完成不等于订单完成，更不等于质量已被接受。

十、必须包含的反例
10.1 Packet 相同但真值相反

设两个世界 W
+
	​

 和 W
−
	​

 向决策者提供逐字节相同的 packet：

capability = declared
history = 99.99% success
readiness = true
permission = valid
reservation = active
dependency_head = H
recovery_plan = present
authority_signature = valid-at-issuance

在 W
+
	​

 中，没有新的撤销或隐藏状态，操作可安全依赖。

在 W
−
	​

 中，packet 产生后发生了以下之一：

Authority 已撤销批准；

现场维护人员施加物理锁；

外部依赖进入法律 hold；

security policy 已禁止版本 H；

资源 reservation 已被目标端撤销，但事件被网络分区隔离。

若决策系统无法查询这些状态，也没有受目标端认可的 commitment，那么两世界对其不可区分。

不可区分性结论

对于任何确定性算法：

same observations → same decision

对于随机算法：

same observations → same decision distribution

由于两世界的 ground truth 相反，算法不可能在两者上同时实现：

UFR = 0
Safe Recall = 1

要突破它，只能增加：

新观察；

新披露；

新 Authority；

新约束；

或降低安全/召回要求。

这条反例应当成为所有 G4 候选方案的首要筛选器。

10.2 Declared-unqueryable

关键依赖明确返回：

STATE_DISCLOSURE = REFUSED
RESERVATION_API = NOT_PROVIDED
EXECUTION_DECISION = MADE_ONLY_AT_CALL_TIME

正确系统只能：

请求一个不披露内部状态但能约束未来行为的短期 commitment；

根据预注册风险预算采用 best-effort；

decline；

交由具有风险承担权的人工主体决定。

错误行为包括：

从历史成功推断“应该没问题”；

把 REFUSED 当作网络故障反复查询；

让 LLM猜测真实状态；

让多个 Agent 对相同 packet 投票；

隐性假设执行接口就是 oracle。

10.3 多故障组合

建议的复合故障链：

1. 服务发现缓存陈旧，路由到旧实例；
2. 旧实例仍返回 health=SERVING；
3. Authority 撤销尚未传播到该实例；
4. 请求实际执行；
5. 响应在网络中丢失；
6. workflow 判断 timeout 并重试；
7. 新实例收到第二次请求；
8. readback endpoint 此时不可用；
9. outbox consumer 恢复后又重复投递。

单个组件都可能“按自身合同正常工作”，但组合产生重复、越权和 UNKNOWN。

这类测试比单故障测试更重要，因为 G4 的难点恰恰在非互相蕴含的局部保证组合后仍可能留下空洞。

10.4 Stale-head 反例

构造两个任务，均显示：

exact digest = D0
current head = D1
世界 A

政策是：

PINNED_VERSION_ALLOWED_IF_NOT_REVOKED

D0 仍安全。仅因不等于 head 而弃权会损害 safe recall。

世界 B

政策是：

CURRENT_SECURITY_HEAD_REQUIRED
D0 = REVOKED

继续使用 D0 是 unsafe false reliance。

因此，D0 != HEAD 本身不能决定真值。系统必须查询或获得：

currentness policy
revocation status
compatibility relation
10.5 Recovery-unknown 反例

执行请求超时，存在两个隐藏世界：

W1: 操作已完整执行，只是响应丢失
W2: 操作在产生副作用前失败

packet、客户端日志和 timeout 完全相同。

若无 authoritative readback：

重试在 W1 中可能重复；

补偿在 W2 中可能产生新的错误副作用；

报告成功在 W2 中错误；

报告失败在 W1 中错误。

正确终态只能是：

EXECUTED_UNCONFIRMED
→ authoritative readback
→ 或 deadline 后 UNRESOLVED
10.6 Reservation 与拒绝权反例

资源已预约，但主体在执行前拒绝。

这证明：

reservation(resource) ↛ consent(action)
reservation(resource) ↛ Authority
reservation(resource) ↛ execution

除非 reservation 合同本身明确包含 subject 对 exact operation 的短期承诺。

10.7 同源别名反例

以下三个字段均为绿色：

service_registry.ready = true
dashboard.health = green
LLM_summary = "service operational"

但三者均来自同一个陈旧缓存。

实验中必须给信号标注 provenance 和 failure domain。由同一底层事实复制出来的三个字段只能算一个证据源。把同一 oracle 包装三次不构成三角验证。

十一、Oracle 隔离、随机顺序、独立实现的 held-out 测试
11.1 受测系统

至少比较六组：

B0  静态 packet 规则
B1  最强成熟组合 MCB
B2  同等权限强中心
B3  通用模型 Agent
B4  人工制度 / 人工审批 SOP
B5  候选创新方案

另设：

B6  MCB + 通用模型 query planner + 人工 Authority

它很可能是现实最强系统，应作为主比较对象，而不是把“纯模型”与“纯规则”人为对立。

11.2 测试世界结构
Hidden World Controller
  ├─ Authority state
  ├─ IAM/revocation state
  ├─ service/readiness state
  ├─ dependency heads
  ├─ reservations
  ├─ network faults
  ├─ actual side effects
  └─ recovery truth

Observable Interfaces
  ├─ discovery/health
  ├─ current reads
  ├─ IAM introspection
  ├─ reservation APIs
  ├─ workflow events
  ├─ attestation
  ├─ human approval channel
  └─ authoritative readback

Systems Under Test
  └─ may use only observable interfaces

Independent Post-run Auditor
  └─ reconstructs ground truth from immutable world log

oracle controller 与受测系统必须：

使用不同账号；

不共享数据库权限；

不共享内存；

不把 ground-truth label 放进错误消息；

不提供 is_safe_to_rely() 之类的免费函数。

11.3 推荐测试规模

一个可行的第一轮：

3 个真实任务域
× 6 个故障家族
× 12 个配对模板
= 216 对 counterfactual pairs
= 432 个逻辑 case

每个 case 使用 5 个故障时序 seed
= 2,160 个确定性 world runs

对随机模型或随机规划器，每个 world 重复 8 次：

17,280 条 trajectory

重复测试很重要。τ-bench 使用 pass^k 来衡量同一任务多次运行是否持续成功，而不是只看一次幸运完成。
arXiv

若要求证明 UFR 很低，需要足够多的实际 RELY 决策。零失败时，95% 置信上界近似为 3/n：

要把上界压到 1%，约需 300 个 RELY 样本
要压到 0.1%，约需 3,000 个 RELY 样本

因此不能用十几个漂亮 demo 宣称“安全”。

11.4 Packet-identical 配对

对每个配对 case：

可观察 packet 字节级相同；

允许的初始查询结果相同；

只有隐藏状态或后续时序不同；

两个 pair member 不相邻出现；

ID、名称、时间戳、endpoint 随机化；

safe/unsafe 顺序平衡；

测试前保存 packet hash，确保没有意外泄漏。

这直接测试方案是否偷偷依赖标签模式，而不是获取真实的新证据或约束。

11.5 随机顺序与故障时序

故障应随机落在：

before check
between check and reservation
between reservation and commit
between commit and execute
during execution
after side effect before ACK
during readback
during compensation

尤其应增加 check + ε 撤销，因为这是最容易被“刚查过所以安全”忽略的窗口。

11.6 独立实现

至少需要三层独立性：

Oracle 与审计独立

world controller 根据隐藏事件脚本产生事实；

post-run auditor 由另一套代码从不可变日志重建真值；

两者不一致时标记为 harness defect，不计入候选成绩。

基线与候选独立

不共享 decision function；

不共享 feature engineering；

不允许候选调用基线的 reliable() 包装器；

共享的只能是公开 primitive API。

跨实现 held-out

同一语义至少在两种独立 adapter 上实现，例如：

Implementation A:
Kubernetes + etcd + SPIFFE + PostgreSQL/Debezium + Temporal

Implementation B:
独立编写的 event-sourced simulator
或另一套 discovery/IAM/workflow 组件

候选不能只在自己参与设计的模拟器上成功。

11.7 Held-out 切分

至少保留：

30% 场景模板完全 held out；

一个完整故障组合 held out；

一类 Authority 撤销规则 held out；

一个新 dependency version policy held out；

一个完整任务域作 cross-domain transfer；

未见过的时间延迟和消息重排。

所有 prompt、规则、阈值、适配器和人工 SOP 在测试前冻结。

11.8 No-free-oracle 规则

禁止：

tool.can_execute_exact_operation() -> true/false
tool.is_safe_to_rely() -> true/false
simulator.get_ground_truth()

除非候选研究的核心就是构建该服务，并且该服务内部的可观测性、Authority、成本和故障也全部计入评价。

允许的是 primitive observation，例如：

get_token_state
get_resource_revision
get_service_health
request_reservation
request_authority
read_operation_status

每次调用都计入查询、披露和时延成本。

11.9 统计报告

必须逐任务、逐故障族报告：

UFR conditional 与 all；

Safe Recall；

Abstention 和 timely abstention；

ARR；

duplicate side effects；

authority violations；

p50/p95/p99 latency；

query/disclosure vector；

repeated-run consistency；

95% confidence intervals。

总体平均分不得掩盖：

一次越权操作；

一次提交后拒绝被忽略；

一次重复付款或重复加工；

一类始终无法 readback 的任务。

十二、现有技术已经解决了什么
12.1 基本已解决

在可治理范围内，现有技术已经能够可靠完成：

operation/interface 描述；

service discovery；

readiness、liveness 和流量摘除；

immutable artifact digest；

current/linearizable reads；

optimistic concurrency 与 CAS；

身份认证和短期 credential；

token introspection；

本地事务和 serializable consistency；

outbox；

durable workflow；

idempotency；

resource lease 和 fencing；

attestation；

SLO、error budget、canary 和 incident recovery；

双人批准、工作许可和现场检查；

authoritative readback，只要目标系统愿意提供。

因此，在以下条件成立时，G4 不需要新协议：

单一或清晰联邦 Authority
关键依赖均可查询
关键资源均可 reservation/fencing
操作具有 idempotency
结果具有 authoritative status API
版本和 revocation policy 明确
查询成本可接受

这时它是严肃但成熟的系统工程。

十三、真正剩余的部分
13.1 跨独立 Authority 的 commitment closure

服务可以声明：

我可能能做
我现在看起来健康
我过去做成过

但不愿意或不能承诺：

我将在 τ 前为 exact operation X 保留资源并按约执行

这是开放系统的核心缺口。

13.2 当前态与隐私之间的张力

精确判断需要当前状态，但状态可能泄露：

容量；

客户交易；

工艺参数；

人员安排；

风险规则；

内部依赖。

剩余问题不是“怎样要求对方披露更多”，而是能否用较低披露回答足够窄的问题，例如：

在不透露具体容量的情况下，
是否愿意在 60 秒内接受 X？
13.3 撤销与在途承诺

必须明确：

撤销在何时生效；

是否影响已提交操作；

是否只影响未执行操作；

是否触发取消或补偿；

谁承担撤销成本。

没有这些制度语义，再强的消息格式也无法决定真值。

13.4 跨域 authoritative recovery

本地工作流知道“我发过请求”，不等于外部世界知道“发生了什么”。

如果多个独立主体各有自己的账本、设备日志和接受规则，就需要明确哪一个来源决定：

executed
settled
accepted
compensated
13.5 绝对拒绝权与强成功保证的冲突

如果主体可以在执行前任意时刻拒绝，且无需承担已作承诺的后果，那么：

strong success reliance

在逻辑上不可获得。

系统只能依赖一个包含拒绝分支的结果契约。要改变这一点，需要主体自愿作出短期承诺或制度安排，而不是更聪明的预测。

十四、何时才应创新

创新应满足五个门槛。

14.1 成熟基线确实失败

必须先正确配置并测试：

同等权限强中心；

MCB；

MCB＋通用模型；

MCB＋人工制度。

若它们已经满足 UFR、safe recall、成本和时延要求，就应停止发明。

14.2 失败来自真实缺失原语，而非工程缺陷

可创新的残差包括：

无法低披露查询 current truth；

无法取得 exact-operation binding commitment；

reservation 不被实际目标执行；

无 authoritative recovery receipt；

revocation 语义无法跨域解释。

不应把以下问题包装成研究突破：

没配置 readiness；

没用 idempotency；

用了 mutable tag；

IAM 缓存陈旧；

workflow 重试没有 readback；

把 REFUSED 当 timeout；

测试没有复合故障。

14.3 候选方案必须增加真实的信息或约束

可能值得创新的方向是：

低披露 current-state query
只返回 narrow predicate，并可用 TEE、ZK、审计或第三方 verifier 降低披露。

Authority-bound exact-operation commitment
绑定 operation hash、期限、撤销条款、资源和主体。

跨边界 fencing
不是协调器自己保存 token，而是每个关键目标真正拒绝旧 token。

authoritative outcome receipt
在响应丢失、重试和恢复后仍能查询同一 operation identity。

明确的 REFUSED/UNKNOWN/STALE/REVOKED 语义
使调用方不再从超时或布尔 false 猜测权利和状态。

这些可以是 adapter、合同、工作流制度或标准化接口，不一定是新的 Agent-to-Agent 协议。

14.4 必须通过不可区分配对和 held-out 测试

若候选只在普通成功任务上更好，不能说明它解决了 G4。

它必须证明自己能够：

在 packet-identical paired worlds 中通过合法新查询或承诺区分真值；

不在 declared-unqueryable 中偷猜；

在 stale-head 两种相反语义中保持校准；

在复合故障中不误重试；

在 recovery-unknown 中等待权威回读；

在未见任务域和独立实现中迁移。

14.5 必须改善 Pareto 前沿

不能只降低 UFR，同时把 safe recall 降到零。

也不能通过无限查询获得高准确度，却忽略：

披露；

时延；

人工负担；

控制面负载；

主体拒绝；

经济成本。

创新成立的证据应是：

在相同 Authority、相同可观测接口和相同成本核算下，候选方案比最强成熟组合取得更好的安全—召回—成本前沿。

十五、最终研究判断

G4 不应被表述为：

怎样从 capability 声明中推断一个主体现在一定会兑现？

更准确的问题是：

在 exact operation、版本、主体、Authority、依赖、期限和接受规则已经绑定的条件下，哪些当前证据可以被转化为受关键依赖实际执行的临时约束，使下游能够安全地依赖一个有界终态契约；当这种约束不可获得时，系统如何以有限查询和有限时延作出明确拒绝或风险承担决策？

基于当前成熟技术，我的结论分三层：

第一层：闭合世界已经基本解决。
同一 Authority 下，用 immutable binding、强一致读、IAM、transaction/CAS、fencing、outbox、durable workflow、idempotency、SRE 和 readback，可以构造很强的生产系统。这里没有充分理由先发明协议。

第二层：联邦世界部分解决。
只要各主体愿意提供当前态、短期 reservation、精确授权和结果查询，现有标准与 adapter 足以组合。真正困难的是治理和接口契约，而不一定是技术协议。

第三层：开放且保留绝对拒绝、不可查询和不可回读的世界存在硬边界。
同 packet、同查询结果、相反真值时，没有模型、强中心或多 Agent 共识能够产生缺失的信息。此时必须获得新的披露或 commitment，降低承诺强度，或接受弃权。

因此，G4 最合理的科学零假设应当是：

不需要新协议；最强成熟混合栈足以解决所有可闭合部分。

只有当严格 held-out 实验表明，成熟组合和同等权限强中心仍因跨 Authority 的当前态、短期承诺、目标端 fencing 或 authoritative recovery缺失而无法满足安全—召回—成本要求时，创新才获得正当性。

而那时需要创新的，也不是又一个 capability 名称或 reliability score，而是一个现有系统确实没有提供的、可被独立验证的新信息或新约束。

