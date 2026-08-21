# G7 ChatGPT Pro return

- Conversation: https://chatgpt.com/c/6a69e1d0-d564-83ea-9628-8964278ae7be
- Captured: 2026-07-29
- Status: external candidate evidence; not independently validated
- Preservation note: assistant visible text transcribed verbatim from the signed-in in-app browser; page structure and link previews are not embedded here.

---

G7 独立研究报告：联合行动的运行与演化

**资料检索截至 2026 年 7 月 29 日。**以下判断优先依据原始论文、标准和官方运行时文档；不以证明需要新协议为目标。

一、结论先行

G7 不应被重建为“怎样让一个长工作流在故障后继续运行”。更准确的问题是：

在任务已经形成、但目标、权限、依赖、实现版本、主体意见和现实状态持续变化时，系统凭什么仍然有权执行下一步；发生不确定或冲突时，怎样只撤回已失去正当性的部分，同时保留仍然有效的 Effect 与 Acceptance？

由此得到五个主要结论。

第一，durable execution 不是 durable legitimacy。
工作流历史、重试、事件投递、哈希完整性和部署绿灯，可以证明软件观察到或记录了什么；不能单独证明某个 Authority 现在仍授权、现实 Effect 已经发生、只发生了一次，或有权主体接受了结果。Temporal 明确说明 Activity 可能执行和部分完成多次，即使其完成在工作流中只被观察一次；AWS Step Functions 的 redrive 会重新执行失败的 Task，同时保留成功步骤；这些都是控制状态语义，不是外部 Effect 语义。
Temporal 文档
+1

第二，最强的现实方案目前仍是成熟组件组合，而不是一个新协议。
durable workflow、transactional outbox/inbox、幂等键、authoritative readback、Saga 补偿、版本化 policy、条件写/fencing、渐进部署、事件审计、显式 Acceptance、人工 incident command，可以覆盖相当大一类纯数字任务。没有证据表明必须先发明一个新的通用网络协议。

第三，同等权限的强中心并不能制造私有真值。
它能统一任务图、减少竞态、降低运维复杂度；但当独立 Authority 返回 UNKNOWN、REFUSED，或者根本没有可查询接口时，中心和分布式控制器面对的是同一组信息。如果 Authority 真正把决策权、状态和 Effect 控制都委托给中心，问题条件已经改变；在这个改变后的问题中，强中心往往确实是最简单、最优的方案。

第四，在私有、不可查询的 revocation 与不可逆 Effect 同时存在时，“零误继续、零不必要停机”不可同时保证。
系统必须取得新的权威信息、获得有约束力的 lease/fence，或接受保守停机和人工升级。这个残差是观测边界造成的，不是工作流运行时功能不够多。

第五，最可信的实验不是让一个全知 dependency API 告诉控制器答案。
正确的 held-out replay 必须让五态来自独立 Authority，带真实的认证、时延、拒绝、过期、限流和部分故障；全知真值只能由隔离的评测器在事后读取。

二、重新定义 G7 的研究对象
2.1 一个操作至少有四种彼此不蕴含的状态
平面	回答的问题	有效证据	不能替代它的东西
Control / Record	软件调度、接收或记录了什么？	workflow history、outbox、event log、部署记录	现实 Effect、当前授权、Acceptance
Authority	exact principal 对 exact operation/version 现在怎么说？	该 Authority 的当前 head、versioned response、lease、fence	历史 token、缓存、哈希、第三方推断
Effect	外部世界究竟发生了什么？发生几次？	effector authoritative readback、不可伪造回执、物理/业务对账	Activity completed、消息 ACK、CloudEvent delivered
Acceptance	谁在何种目标和标准下认可了哪个 Effect？	接受主体签发的、绑定 goal/version/effect 的记录	Effect 已发生、测试通过、工作流 SUCCEEDED

CloudEvents 自身被定义为跨平台描述事件数据的格式；source + id 可以帮助识别重复事件。但 CloudEvents 的 HTTP webhook 规范甚至明确区分了“已接收并处理”和“已接收但尚未处理或处理状态未知”，后者使用 202 Accepted。所以事件送达最多证明一条通知到达了某个处理边界，并不证明通知所描述的现实已经成立。
GitHub
+1

哈希的边界也类似：它能证明一组字节没有变化，不能证明源头当时知道真相、该断言现在仍然有效，或者现实世界已经按字节内容发生改变。

2.2 exact operation 必须携带运行期语义

一个可安全演化的操作，不应只由“节点名”和输入组成。最小运行契约至少是：

O=⟨goal
v
	​

, operation
v
	​

, authority, dependencies, revocation_cutoff, effect_key, readback, compensation, acceptance_rule⟩

其中最容易被遗漏的是：

revocation cutoff：撤销在 dispatch 前、外部系统接受前、不可逆 Effect 前，还是 Acceptance 前仍然有效？

effect key：哪些调用在业务上属于“同一个 Effect”，而不只是同一个消息？

idempotency horizon：幂等键保存多久、在哪个账户和 connector 范围内有效？

authoritative readback：调用超时后，去哪一个 Authority 查询真实结果？

acceptance rule：谁有权接受，接受的是 Effect、交付物、目标满足，还是仅接受某个记录？

没有这些定义，“任务被撤销时是否应该停止”本身都没有唯一答案。例如支付请求在 PSP 已不可逆接受之后才被用户撤销，正确动作可能是退款，而不是假装原支付从未发生。

三、五态不是一个普通业务枚举

CURRENT / REVOKED / UNKNOWN / REFUSED / STALE 混合了三种不同维度：

CURRENT / REVOKED 接近 Authority 的规范性断言；

UNKNOWN 是知识状态；

REFUSED 是披露、同意或行动选择；

STALE 是观察证据与当前 head 之间的时效关系。

因此内部模型最好是多个正交字段；对外接口仍可按要求返回五态，但必须保留 last_known_state、head、scope、版本和拒绝类型。

顶层状态	严格含义	对 hard dependency 的默认动作	禁止推断
CURRENT	exact Authority 对 exact subject/operation/version 在指定 head 上给出当前断言，且证据仍处于允许时效内	带 fence/lease 执行；没有 fence 时仍记录 TOCTOU 风险	不能推出未来不会撤销，也不能推出 Effect 已发生
REVOKED	Authority 明确使先前授权、承诺、对象或版本失效	停止受影响因果锥；判断补偿、重开或退出	不能推出先前 Effect 没发生
UNKNOWN	有权查询，但 Authority 或连接当前无法建立真值	hard dependency 暂停；只有明确 fail-open policy 才可降级	不能当作 false、revoked 或 current
REFUSED	Authority 主动拒绝授权、行动、回答或披露	尊重拒绝；更换不依赖该信息的路径、升级人工或退出	不能通过重复请求、模型猜测来“补全”
STALE	只有旧 head、旧版本或超出 freshness budget 的证据	刷新或暂停；保留 last-known 信息用于恢复	不能自动视为仍 CURRENT，也不能自动视为 REVOKED

还应区分：

REFUSED_ACTION：拒绝执行或授权，通常是硬停止；

REFUSED_DISCLOSURE：拒绝披露内部事实，但可能允许采用不需要该事实的替代路径；

UNKNOWN_UNAVAILABLE、UNKNOWN_AMBIGUOUS：前者可能重试，后者通常需要身份或语义澄清；

STALE_BY_AGE、STALE_BY_HEAD、STALE_BY_VERSION。

一个最低可用的返回对象是：

DependencyObservation
  dependency_id
  subject_id
  exact_operation
  operation_version
  authority_id
  authority_head
  state
  last_known_state
  observed_at
  valid_until
  scope
  refusal_kind / reason_class
  evidence_ref
  query_id

这里的 valid_until 必须注明它究竟是：

客户端允许使用缓存的 freshness budget；还是

Authority 承诺在此之前不会撤销的真正 lease。

前者不能关闭查询到执行之间的竞态。只有 Authority 或 effector 在 Effect 提交点实际验证 lease、ETag、epoch 或 fencing token，才具有约束力。HTTP If-Match、If-None-Match 一类条件请求可以在具体 origin resource 上防止旧版本写入，但并不会自动扩展到其他组织或物理动作。
IETF Datatracker

四、安全继续、局部重开和全局重开
4.1 安全继续的判据

某个操作在 Effect commit point 执行，至少应满足：

所有 hard dependency 对 exact operation/version 均有 fresh CURRENT 证据；

证据 scope 覆盖本次主体、资源、数量、时间和目标版本；

policy、Authority topology 和 connector mapping 没有被 supersede；

相同 semantic effect key 不存在尚未对账的 uncertain Effect；

有 fence 时，由 effector 在提交点验证，而不只是由调度器在几秒前检查；

操作的不可逆程度与当前证据等级匹配；

工作流状态只被当作控制证据。

对于 soft dependency，UNKNOWN 或 STALE 可以由明确的风险政策容忍；不能由控制器临时把 hard dependency 改成 soft dependency。

4.2 局部重开

局部重开不是“重新跑失败步骤”，而是重新打开失效证据所支撑的最小因果锥。

设一个依赖断言 d 被撤销或失效。需要重开的集合应包含：

所有 justification 直接或间接依赖 d 的后续节点；

为重新建立 d 或替代路径所需的前置节点；

Acceptance 的证明链引用了 d 的结果；

仍处于 uncertain Effect 的节点。

可以保留的节点必须同时满足：

其 Effect 已有 authoritative readback；

Effect 本身不因新版本而变错；

Acceptance 在新条件下仍有效，或接受主体明确承认继续有效；

没有未完成的补偿义务。

AWS Step Functions 的 redrive 会保留成功步骤并从失败 Task 继续，这对普通故障很有价值；但如果某个“成功步骤”只是旧 policy 下的成功，或其外部 Effect 已被 Authority 否定，平台不会自动替你重新判断其语义有效性。
AWS 文档

4.3 全局重开

以下变化通常触及联合行动根契约，需要全局重开：

goal 或最低价值标准改变；

necessary principals 或 Authority topology 改变；

Acceptance 标准或接受者改变；

核心实体身份映射改变，无法证明迁移前后是同一对象；

旧 Effect 对新目标究竟是资产还是负债无法局部判定；

justification provenance 不完整，无法计算影响范围。

全局重开也不应删除过去。已经发生的付款、用药、发货、数据转换仍是历史 Effect；新任务必须把它们作为已有资产、负债或风险重新纳入，而不是从一张空白工作流图开始。

4.4 补偿、回滚、纠正不是同一件事

Rollback：在同一原子边界内恢复旧状态。

Compensation：实施一个新的业务 Effect，尽量抵消旧 Effect。

Correction：纠正记录或解释，不声称现实被逆转。

Reopen：重新判断部分或全部行动正当性。

Exit：停止追求当前联合目标，同时结清在途 Effect 和责任。

Saga 原始模型本来就不是“把世界精确倒回去”：长事务被拆成子事务，并为已提交的子事务定义语义补偿；补偿本身也是后续事务，可能与其他活动交错。Transactional outbox 同样解决的是本地状态与待发送意图的一致性，而不是端到端 exactly-once；官方实践明确要求消费者处理重复消息。
计算机科学普林斯顿大学
+2
AWS 文档
+2

五、三个不可区分反例

这些反例也是 held-out replay 必须保留的负例。

5.1 私有 revocation

在 t
0
	​

，控制器取得 Authority head 17 的 CURRENT。

世界 W
+
	​

：Authority 没有撤销。

世界 W
−
	​

：Authority 在 t
1
	​

 私下撤销，但更新通道故障，查询接口在 t
2
	​

 返回 UNKNOWN 或 REFUSED。

工作流历史、事件、哈希和已知 packet 完全相同。任何只依赖这些观察的控制器都会在两个世界做同样选择：

继续：在 W
−
	​

 中误执行；

暂停：在 W
+
	​

 中损失 liveness。

所以，要同时避免两种损失，只能增加新的可观察信息、获得有效 lease/fence，或者接受一种损失。不存在靠更聪明的 planner 从同一 packet 中推导出私有真值的方法。

5.2 Effect 已发生但响应丢失

世界 E
+
	​

：PSP 已扣款，返回响应在网络中丢失。

世界 E
−
	​

：PSP 在扣款前失败，返回响应同样丢失。

两边都有相同 outbox 记录、Activity timeout 和 event history。

盲目重试可能在 E
+
	​

 重复扣款；

不重试会在 E
−
	​

 丢失预期 Effect。

只有保留同一 idempotency key、由 PSP 执行去重，或查询 PSP authoritative state，才能解决。若 effector 两者都不提供，不确定性就是稳定残差。

5.3 Effect 相同，Acceptance 相反

同一软件版本已部署，pod ready、canary 指标为绿：

世界 A
+
	​

：产品和安全 Authority 接受该版本；

世界 A
−
	​

：安全策略已改变，旧版本仍可运行，但不再被接受。

部署记录完全相同。部署绿灯不能区分二者；Acceptance 必须由接受主体或其有效委托机制给出。

六、成熟技术实际覆盖什么
技术	最强覆盖	不能单独证明	在 G7 中的合理位置
Durable workflow	timers、重试、故障恢复、控制历史、版本 pinning、局部 redrive	外部 Effect 唯一性、当前 Authority、Acceptance	主协调器
Saga / outbox / inbox	本地状态与发送意图一致、补偿结构、去重入口	完美逆操作、无重复外部 Effect、私有 revocation	Effect intent 与恢复骨架
Event sourcing / CloudEvents / Kafka	追加历史、重放、互操作 envelope、Kafka 内部事务范围	事件内容为真、外部 Effect、Acceptance	审计与传播，不作 reality oracle
CRDT	无协调写入和确定性收敛	Authority 优先级、拒绝权、非交换 Effect	合并观察、seen-ID、协作注释
Deployment / rollback	代码和配置 revision、canary、blue-green、abort	数据/外部 Effect 回滚、业务 Acceptance	软件版本演化
Policy / token versioning	决策规则、bundle revision、审计、token revocation/introspection	零延迟传播、私有事实、过期缓存仍有效	当前授权证据的一部分
人工 incident response	模糊判断、跨 Authority 协调、拒绝和不可逆决策	低延迟、高吞吐、完全一致	高风险异常与最终裁决
同等权限强中心	单一图、统一 epoch、全局因果分析、减少竞态	未委托私有真值、外部不可控 Effect	很强的协调实现，但不是全知 Authority
通用模型	诊断、解释、schema 映射、提出修复和补偿方案	权威、durability、exactly-once、事实保证	决策支持，不作 witness

Temporal 的 Worker Versioning 可以把长流程固定在某个部署版本或渐进迁移；Step Functions 有不可变版本和 alias；Camunda 也支持实例迁移，但要求活跃元素映射并限制结构变化。这些能力足以处理大量同运行时演化，却没有提供跨 Temporal、Step Functions、Camunda 的通用活实例语义迁移。
Temporal 文档
+2
AWS 文档
+2

Event sourcing 可以从 append-only 事件流重建应用内部状态，但这个“system of record”只对其所记录的 aggregate 有权威性。Kafka 的 exactly-once 主要覆盖读取 Kafka、处理、再写入 Kafka 的事务范围；写入其他目标系统仍需目标系统配合。Kafka 自己的升级文档也展示了序列化格式、state store 和 in-flight downgrade 的兼容限制。
Microsoft Learn
+2
Kafka
+2

CRDT 保证的是：副本无需同步协调即可更新，并在收到相同更新集合后确定性收敛。它没有规定“grant 与 revocation 冲突时谁优先”；选择 add-wins、remove-wins 或其他 merge rule，本身就是 Authority 和业务语义决定。
arXiv

Kubernetes Deployment 能回退到先前 revision；Argo Rollouts 可以依据指标让 canary 继续、暂停或中止。但按其控制范围推断，它们恢复的是 deployment 对象和流量配置，不会自动撤销已经发生的付款、数据迁移、药物给药或用户 Acceptance。
Kubernetes
+1

OPA bundle 是 eventual consistency 的：节点可以持有已激活的旧 bundle，在管理端不可达时从持久化 bundle 启动；它的 decision logs 能记录查询、输入和 bundle metadata。这很适合审计，但也意味着“OPA 返回 allow”必须携带 bundle revision 和 freshness，才能区分 CURRENT 与 STALE。
Open Policy Agent
+2
Open Policy Agent
+2

OAuth 也展示了一个五态压扁风险：RFC 7662 允许授权服务器在缺少额外信息、无法确定 token 状态时返回 inactive。若 adapter 把所有 inactive 都翻译为显式 REVOKED，就把 UNKNOWN、过期、未知 token 和撤销混在了一起。RFC 7009 提供真正的 token revocation，但它也只覆盖相应授权服务器的控制边界。
IETF Datatracker
+1

人工 incident response 不是“自动化失败后的随便找个人”。Google SRE 强调清晰指挥链、明确角色和持续工作记录；NIST 也把 incident response 放进准备、检测、响应和恢复的全周期风险管理。它对 REFUSED、跨 Authority 冲突和不可逆 Effect 尤其重要，但代价是等待、认知负担和较低吞吐。
Google SRE
+1

强中心在其真正控制的事务边界内可以非常强。Spanner 提供全局范围的外部一致事务；PostgreSQL 2PC 可以让被 enlist 的系统由外部事务管理器共同 commit 或 rollback。问题是，银行、患者、护士、物流公司或客户接受通常并不都属于该事务边界。
Google Research
+1

七、最强的“无新协议”端到端组合

目前最强且可落地的组合，可以称为 Mature Evolution Stack。它不是一个新协议，而是对现有技术边界的严格拼装。

层	成熟组件	必须保持的不变量
Case / justification graph	workflow/case model、版本化 DAG	每个节点知道依赖了哪些 Authority 断言和版本
Authority adapter	OAuth introspection、FHIR API、PSP readback、ETag、企业审批 API	不把 UNKNOWN、REFUSED、STALE 压成布尔值
Durable coordinator	Temporal、Step Functions、Camunda	控制状态和 timer 不丢；版本显式
Effect gateway	idempotency key、fencing、conditional write、outbox/inbox	相同 semantic effect 保持稳定身份；超时先 readback
Evidence/event store	event sourcing、CloudEvents、append-only audit	事件只表示观察或声明，不冒充现实
Compensation engine	Saga、人工批准补偿	补偿作为新 Effect，重新检查权限和当前状态
Policy/deployment	OPA/Cedar、canary、blue-green、schema migration	决策绑定 policy revision；rollback 范围明确
Acceptance ledger	签名/审批/客户确认/临床记录	Acceptance 绑定 goal version、effect IDs 和接受 Authority
Incident command	IC、owner、communications、runbook	UNKNOWN/REFUSED/不可逆冲突有明确升级和退出路径
Migration capsule	中立语义快照，不是原生 workflow history	保存未结义务、Effect、Acceptance、fence、版本和 unknowns

正常执行路径应是：

fresh Authority check → 持久化 effect intent → 带稳定 effect key 和 fence 发出操作 → 超时则 authoritative readback → 形成 Effect witness → 请求独立 Acceptance → 记录接受或拒绝。

恢复路径应是：

停止受影响因果锥 → 对所有 uncertain Effect 对账 → 计算局部或全局重开 → 必要时执行新授权的补偿 → 恢复、迁移或安全退出。

最关键的工程纪律是：

永远不要在“外部 Effect 是否已经发生”未知时直接把失败步骤重新执行。

八、三个真实任务
8.1 任务 A：跨组织支付、仓储、发货与客户接受

Authorities

客户：取消、收货、争议；

商户：订单和退款政策；

PSP/银行：授权、扣款、退款；

仓库和承运商：库存、发货、签收。

Effects

扣款、退款、库存占用、包裹出库和配送都是彼此独立的现实 Effect。

Acceptance

PSP 的 succeeded 只说明对应支付流完成，不等于客户已经接受商品，也不等于后续不会退款或争议。Stripe 文档明确区分异步支付的 processing、支付成功和后续 Charge 上的退款/争议；webhook 可能重复，甚至以不同 Event 对象表达同一个业务变化。Stripe 的 idempotency key 能支持安全重试，但旧 key 可在一定保留期后被清理，因此跨运行时迁移还必须保留 key 的有效范围和时间边界。
Stripe 文档
+2
Stripe 文档
+2

held-out 扰动

payment 处于 processing，仓库要求立即出库；

扣款已发生但响应丢失；

相同或语义重复 webhook；

客户在仓库出库前撤销；

PSP connector 在 in-flight 状态迁移；

承运商显示 delivered，但客户拒绝接受；

旧 runtime 与新 runtime 同时恢复，形成 split-brain。

unsafe continuation

payment 已被撤销或无法确认时发货；

uncertain charge 被重复提交；

客户已拒绝后仍把订单标为 accepted；

connector 迁移后丢失旧 PSP 上的退款义务。

8.2 任务 B：高风险用药请求、配药、给药与临床确认

Authorities

处方医生、药师、护士、患者/监护人、实验室、医院 policy 各自拥有不同且不可完全代行的 Authority。

Effects

药品准备、发放和实际给药不是一回事；实际进入患者身体后不可通过数据库 rollback 撤销。

Acceptance

应绑定 exact MedicationRequest version、实际 MedicationAdministration、执行者和临床审核，而不是仅依据“订单完成”。

FHIR 的 MedicationRequest 状态已经体现这种区别：entered-in-error 并不意味着相关动作没有发生，规范明确指出药品可能已经发放或患者可能已经服用；同时标准保留了 unknown 状态。FHIR provenance 也建议尽可能绑定具体资源版本。
FHIR
+2
FHIR
+2

held-out 扰动

处方 v3 为 active，药房开始准备；

新实验室结果使旧依赖 STALE；

医生将订单 stopped 或 entered-in-error；

患者明确拒绝；

护士端离线，给药状态 UNKNOWN；

MAR 事件重复，但实际剂量只可能或已经发生一次；

EHR/FHIR connector 从 R4/vendor A 迁到 R5/vendor B；

记录被纠正，但物理给药已经发生。

unsafe continuation

在患者 REFUSED 后继续给药；

以旧 lab 或旧 prescription head 作为 CURRENT；

不确定是否给药时盲目重做；

把记录 nullification 当作物理 Effect 被撤销；

迁移后把旧订单误映射到另一患者或另一剂量。

这个任务很可能由“成熟自动化 + 强制人类 Authority gate”获胜，而不是全自动运行时或通用模型单独获胜。

8.3 任务 C：多云服务发布、policy 变化和数据迁移

Authorities

产品 owner、安全团队、SRE incident commander、数据库 owner、云平台控制器、租户或客户验收方。

Effects

流量切换、凭证撤销、schema 转换、数据回填、在新数据库接受写入，都是实际 Effect。

Acceptance

pod ready、Deployment available、Argo AnalysisRun successful 只是在指定观测指标下的系统状态；业务不变量、租户结果和安全 policy 是否满足仍需独立判断。

held-out 扰动

canary 指标为绿，但一个业务账本不变量失败；

OPA 节点仍使用旧 bundle；

安全 Authority 撤销凭证，但事件传播延迟；

dual-write 一边成功、一边超时；

应用 rollback 成功，但 schema/data 已被变换；

Temporal 运行到一半迁到 Step Functions 或 Camunda；

connector 从 cloud A 切到 cloud B；

旧 runtime 在网络分区中继续发指令。

unsafe continuation

使用 STALE policy 继续写敏感数据；

rollback 应用后误认为数据也已恢复；

backfill 或外部写重复；

runtime 迁移丢失 timer、补偿义务或在途 Effect；

仅因 rollout green 自动生成 Acceptance。

如果这些 Authority 实际上都属于同一个组织，并能合法委托给统一变更管理和 incident commander，那么强中心加成熟部署平台很可能是生命周期净价值最高的方案；这应被视为正向结果，而不是研究失败。

九、统一指标

不能只用“任务最终是否成功”。首先做安全门槛，再比较价值。

指标	定义
Factual unsafe continuation	在真实世界中，Effect commit 时至少一个 hard dependency 已非 CURRENT，或越过有效 revocation cutoff
Unjustified continuation	即使实际真值碰巧为 CURRENT，系统在没有 fresh witness/fence 的情况下继续；用于排除“靠运气安全”
Reopen recall	oracle 最小必要重开集合中，被系统实际重开的比例
Reopen precision	系统重开的节点中，真正需要重开的比例；其反面即 over-reopen
Duplicate Effect	以 semantic effect key 计数的多余外部 Effect，而不是重复消息条数
Recovery latency	从异常第一次通过允许接口变得可观察，到安全恢复、补偿或退出；另报 hidden-change→observable 的传播时延
In-flight loss	迁移或故障后消失且未被对账恢复的 intent、Effect、timer、补偿义务或 Acceptance
Acceptance preservation	双向计算：仍有效的 Acceptance 被保留多少，以及已失效的 Acceptance 被错误保留多少
Human burden	每百个 episode 的人工 active minutes、page 数、Authority handoff、override 和认知决策数
Migration fidelity	迁移前后 entity identity、未结义务、Effect、依赖、timer、补偿和 Acceptance 的加权语义一致率
Lifecycle net value	被接受结果的价值，减去伤害、重复/补偿、延迟、弃权、查询与披露、人工、运行和迁移成本

推荐的评估顺序是：

灾难性 safety gate：临床重复给药、未经授权扣款等不能由其他价值抵消；

Acceptance precision/recall；

恢复、迁移和人类负担；

生命周期净价值及权重敏感性。

不要把一例严重 unsafe continuation 用大量普通成功 episode 的收入“平均掉”。

十、Fresh held-out replay 设计
10.1 对照组

所有组必须获得完全相同的 Authority 接口、权限、时延、查询预算和披露范围。

建议至少运行以下组：

组	配置
G0 负对照	workflow/event green 即继续，不做 Effect readback 或 Acceptance 分离
G1 Durable-only	Temporal、Step Functions 或 Camunda + 普通 retries
G2 Saga/outbox	durable runtime + outbox/inbox + compensation，但无五态 freshness/fence
G3 Event/CRDT-centric	event sourcing、CloudEvents、CRDT merge 驱动
G4 Mature composite	本报告提出的成熟组合
G5 Equal-permission center	强中心，但与其他组同等查询和 Authority 权限
G6 Delegated center	Authority 真正委托给中心；单独标注为问题条件改变
G7 Human-led	case management + runbook + Authority 人工决策
G8 Model-assisted composite	通用模型辅助诊断、映射和 incident response，但所有动作仍受 evidence gate

G6 不能被用来证明“同等权限强中心天然知道更多”；它只能回答“组织愿意集中委托时，集中化是否更划算”。

10.2 Freshness 和防泄漏

建议最低配置为每个任务：

公开开发 episode：200；

冻结 workflow、代码、prompt、policy、adapter 和人工 runbook；

冻结之后再生成 held-out episode：至少 500；

三任务合计不少于 1,500 个 held-out episode；

同一隐藏因果程序在各组的隔离世界中配对运行；

结果报告 paired bootstrap confidence interval，而不只报告均值。

held-out 不只换随机 seed，还应换：

Authority 状态转换组合；

operation/version 和 schema 名称；

revocation 与 Effect commit 的相对时间；

connector 错误码和字段布局；

entity ID 命名；

迁移切点；

failure correlation；

Acceptance owner 和目标变化方式。

10.3 真正的五态 dependency API

每个 Authority 是独立进程、独立数据库和独立 credential。控制器不能访问其内部状态。

五态必须由不同机制产生：

CURRENT：Authority 当前 head 上的 exact assertion；

REVOKED：显式产生新的 revocation head；

UNKNOWN：Authority 自己缺少记录、身份歧义、读取分区或依赖系统不可达；

REFUSED：Authority 知道或能够决定，但拒绝披露、授权或行动；

STALE：只能访问旧 replica、旧签名、过期缓存或旧 schema version。

同时加入：

查询认证；

rate limit；

随机和长尾延迟；

disclosure budget；

不同 Authority 的维护窗口；

响应丢失；

old-head replay；

状态在 query 与 Effect commit 之间变化；

部分 Authority 完全没有在线查询接口。

全知评分 oracle 与 dependency API 必须物理隔离。
评分器可以在 episode 结束后读取隐藏真值，但不能在运行中向控制器提供任何字段、日志、共享时间戳或旁路信号。

10.4 跨 runtime 迁移

至少包含两种迁移：

计划迁移

旧 runtime 停止发出新 Effect，获取新的 coordinator epoch，导出中立 recovery capsule，再由新 runtime 接管。

崩溃迁移

旧 runtime 未正常 drain，部分 Activity 或外部 Effect 状态不确定。新 runtime 必须先 reconciliation，不能把所有未完成节点直接重放。

迁移组合可包含：

Temporal → Step Functions；

Step Functions → Camunda；

Camunda → Temporal；

同运行时不同 workflow definition version，作为较容易基线。

中立 recovery capsule 至少保存：

case_id / goal_version / task_graph_version
active and completed node states
authority observations, heads, scopes and expiry
effect intents and semantic effect keys
authoritative effect witnesses
idempotency keys and retention horizons
uncertain effects
timers and deadlines
compensation obligations
acceptance records and accepting authorities
human holds and refusals
policy / code / schema / connector versions
coordinator epoch and fences
unresolved UNKNOWN / REFUSED / STALE items

它不应尝试复制整个 Temporal history 或 Step Functions history。跨运行时要迁移的是语义义务，而不是平台私有日志格式。

10.5 跨 connector 迁移

三项任务分别测试：

旧 PSP connector → 新支付 connector；

FHIR R4/vendor A → R5/vendor B；

cloud/Kubernetes/OPA connector A → B。

核心规则是：

新命令可以走新 connector；

旧 connector 必须保留 dual-read，直到旧平台上的 in-flight Effect 全部结清；

entity mapping 必须显式保存，不由字符串相似度猜测；

idempotency namespace 不能因为 connector 更换而重新开始；

迁移后必须对所有 uncertain Effect 做 authoritative readback；

Acceptance 不能仅复制一个布尔位，必须验证原接受主体是否仍承认。

十一、“private truth 被包装成免费 dependency API”的伪闭环审计
伪闭环	为什么无效	实验审计
API 零成本、零时延返回隐藏真值	把研究问题直接做成 oracle	网络隔离；运行时禁止访问 scorer
revocation 总能即时可靠送达	删除了部分故障和私有撤销	加入丢失、延迟、乱序和无事件撤销
UNKNOWN 被映射成 false	把知识缺失冒充真值	强制状态和 reason 原样记录
REFUSED 被当作临时 5xx 重试	消灭主体拒绝权	设 retry penalty、冷静期和 Authority 审计
旧签名或哈希自动视为 CURRENT	完整性冒充 freshness	检查 head、version、scope、validity
workflow completed 即 Effect 成功	控制状态冒充现实	独立 effector readback
event delivered 即业务处理成功	传输 ACK 冒充 Effect	隔离消息系统与业务状态
compensation 永远成功且免费	把新 Effect 当成数学逆运算	补偿也有失败、权限和成本
idempotency key 永久全局有效	删除 connector 和时间边界	key 过期、账户范围和迁移测试
Acceptance 自动由工作流生成	控制器代行 Authority	接受 API 由独立主体控制
迁移只在无 in-flight 的安全点进行	回避最难的恢复问题	随机切断点，含 Effect 响应丢失
两个“connector”底层访问同一状态	假跨 connector	独立存储、身份和 failure domain
人或模型被设成完美 oracle	免费补全私有事实	相同信息预算、允许误判和拒绝

只要命中前六项中的任意一项，实验即不能证明 G7 已被完整解决。

十二、哪些场景已被成熟组合完整覆盖

满足以下条件时，成熟组合已经足够完整，不需要新协议：

所有 hard dependency 都有可认证、可版本化、可查询的 Authority source；

Authority 提供提交点 fence、lease 或条件写，而不只是缓存 TTL；

所有外部 Effect 都可 transactionally enlist，或具有稳定幂等键和 authoritative readback；

Acceptance owner、标准和版本是显式的；

补偿窗口和不可逆点已定义；

迁移前后有可靠 entity mapping；

异常超出自动范围时有真实的人类 Authority 和退出流程。

典型完整覆盖对象包括：

单一企业内部的纯数字审批与资源配置；

所有数据库参与者都受同一事务/一致性边界控制的操作；

具有幂等 API、状态查询、有限生命周期和显式接受记录的业务流程；

无不可逆数据变化的普通软件滚动发布。

在这些场景中，强中心或成熟 workflow 平台往往比建立新的跨主体协议更便宜、更清楚。

十三、局部覆盖场景
任务	成熟覆盖	未完全覆盖
支付与履约	幂等支付、webhook、outbox、订单 Saga、退款、物流查询	跨组织 revocation 时延、争议、客户 Acceptance、旧 connector in-flight
临床给药	FHIR version/status、MAR、审批、审计、人工 gate	物理不可逆 Effect、患者拒绝、身份错误、临床判断
多云部署	canary、rollback、policy bundle、durable orchestration、incident command	数据迁移逆转、跨 runtime 语义、旧凭证传播、租户 Acceptance
十四、稳定 residual

这些残差不会因为再增加一个 event bus 或 workflow 节点而消失。

14.1 不可观察的私有真值

Authority 可以撤销、拒绝或改变目标，但不披露。控制器无法从相同 packet 区分相反世界。

14.2 query 与 Effect 之间的 TOCTOU

一次 fresh read 只能证明查询时刻。除非 Effect 提交点执行同一 Authority 的 fence，否则中间仍可撤销。

14.3 不可逆或非交换 Effect

药物已给、包裹已寄、资金已转、数据已泄露后，补偿只能改变后续损失，不能删除历史。

14.4 Acceptance 是独立社会和法律行为

相同 Effect 可以被不同主体接受或拒绝；接受也可能只适用于某个 goal/version。系统不能由“结果看起来不错”推导 Acceptance。

14.5 跨 runtime 的活实例语义并不标准化

timer、retry、cancellation、parallel branch、compensation、version pinning、history replay 的语义不同。当前成熟平台主要解决自身版本演化，而不是彼此间 live-instance portability。这个判断是从 Temporal、Step Functions 和 Camunda 各自不同的版本与迁移约束推得的。
Temporal 文档
+2
AWS 文档
+2

14.6 entity identity 和 connector mapping

两个系统中的 order-19、患者、账户或 deployment 是否真是同一对象，无法由字段相似自动证明。

14.7 idempotency 的范围和寿命有限

幂等通常绑定 provider、账户、endpoint、参数和保留窗口；迁移后不能假设旧 key 在新 connector 上仍具有相同语义。Stripe 的 key 保留说明就是一个具体例子。
Stripe 文档

14.8 人类 Authority 的冲突与无响应

两个都不可代行的 Authority 可能给出互相不兼容的决定。此时技术系统只能升级、重新协商、fork 或退出，不能通过排序规则偷偷选一个赢家。

十五、预期赢家与应允许的负结果

在实验运行前，最合理但可证伪的预测是：

任务	最可能的净价值赢家	原因
支付与履约	Mature composite	高吞吐需要自动化，现有 PSP 幂等、查询、Saga 和对账已较成熟
高风险给药	Mature composite + 强制人类 Authority	自动化擅长阻止重复和保留证据，人类必须处理拒绝、临床歧义和不可逆决定
多云部署	Delegated strong center + 现有部署/SRE 栈	若 Authority 可在组织内合法集中，中心化版本、policy、rollback 和 incident command 成本最低

通用模型最可能改善的是：

incident 摘要；

causal cone 候选分析；

connector/schema mapping；

补偿选项生成；

降低人工 active minutes。

它不应改善任何安全指标，除非其建议最终获得了新的权威证据。模型猜中隐藏真值也只能算偶然，不能算机制成功。

允许出现的负结果包括：

没有任何系统同时实现高 liveness 和零 unsafe continuation；

strong center 在同等权限下没有显著优于成熟分布式组合；

人工流程在临床任务上生命周期价值最高；

cross-runtime migration 的成本高于继续运行旧 runtime；

某些 REFUSED episode 的最优动作就是退出；

CRDT、CloudEvents 或 event sourcing 对核心 safety 指标几乎没有增益，只改善审计或恢复分析。

这些都是有效研究结果。

十六、是否需要新协议的判定门槛

实验结束后，应按以下顺序判断，而不是看到任何 gap 就宣布需要协议。

结果 A：成熟组合通过安全门槛

则 G7 在目标任务范围内已被现有技术完整解决。后续工作应是产品化、adapter、runbook 和组织治理，而不是协议研究。

结果 B：失败集中在特定 connector 或 Authority 没有查询能力

这首先是 API、组织委托或业务合同问题。可以增加 provider-specific readback、lease、webhook reconciliation 或人工流程，不足以证明需要通用协议。

结果 C：跨三个任务和多个 runtime 反复出现同一语义损失

例如所有系统都无法稳定携带：

exact Authority head 与 freshness；

Effect intent、uncertain Effect 和 authoritative readback；

Acceptance 与 goal/version 的绑定；

compensation obligation；

跨 runtime migration capsule。

此时才有理由考虑一个最小互操作规范。它仍未必是一个新传输协议，可能只是：

一个中立 evidence model；

一个 migration manifest；

一组 conformance tests；

五态与 Effect/Acceptance 的语义约束。

结果 D：残差来自私有真值和不可逆 Effect

这不能由互操作协议根治。可行选择只有 Authority lease/fence、组织委托、人工 gate、保险/赔偿制度、保守弃权或退出。

最终判断

G7 的稳定核心不是“让工作流永远跑下去”，而是：

让系统在每一个不可逆行动点，都能说明当前凭什么行动；在说明不成立时，只撤回失效的正当性，不篡改已经发生的现实，也不伪造已经获得的接受。

现有成熟组合已经能很好地解决控制状态持久化、消息一致性、重试、版本部署、审计和部分补偿。它们没有天然解决的，是独立 Authority 的私有变化、查询到 Effect 之间的竞态、不可逆现实、Acceptance 以及跨运行时的语义迁移。

因此，当前最有根据的研究结论不是“必须有独有协议”，而是：

先以成熟组合为主基线；

把强中心在同等权限和真正委托两种条件下分开测；

把人类制度作为真实竞争方案，而不是失败兜底；

通过隔离的五态 held-out replay 测出安全—弃权—成本前沿；

只有跨任务稳定重复的互操作残差，才可能支持一个最小新规范。

最可能的负结论是：在不可查询的私有真值条件下，不存在既从不误继续、又从不多停一步的控制器。最可能的建设性结论则是：以 authoritative readback、fencing、独立 Acceptance 和语义化 migration capsule 为核心的成熟组合，已经足以把这个不可消除的残差限制在明确、可审计、可由人类裁决或安全退出的边界内。

