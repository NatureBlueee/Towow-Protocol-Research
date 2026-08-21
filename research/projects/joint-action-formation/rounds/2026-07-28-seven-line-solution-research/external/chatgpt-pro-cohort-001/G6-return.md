# G6 ChatGPT Pro return

- Conversation: https://chatgpt.com/c/6a69e303-a104-83ea-85e3-9e2c29220908
- Captured: 2026-07-29
- Status: external candidate evidence; not independently validated
- Preservation note: assistant visible text transcribed verbatim from the signed-in in-app browser; page structure and link previews are not embedded here.

---

G6 独立重建：现实 Effect 不是一个 workflow 状态
一、核心结论

这条母线首先不是“怎样可靠地宣布完成”，而是：

在多个现实域、多个 owner 和多个权威来源之间，怎样识别并保留一组关于 exact object/version 的事实、采用行为、规范判断与义务解除，而不把控制面的成功记录冒充为目标域现实。

独立重建后，我的结论是：

**Attempt、Effect、Adoption、Acceptance、Settlement 不是五级流水线，而是五种相对于 episode 的角色。**它们可以有局部依赖，但不存在普遍的固定顺序。

最关键的区分不是五层本身，而是四种东西不能混为一谈：

现实中发生了什么；

系统观察到了什么；

哪个 owner 作出了什么有权威的判断；

workflow 根据这些输入推导出了什么状态。

**成熟技术组合已经可以在封闭、可读回、权威明确的数字域中完整解决 G6。**最强组合不是“更强的消息协议”，而是 target-side idempotency/CAS、transactional outbox、durable workflow、权威 readback/reconciliation、独立 owner acceptance、结算 finality 和 SRE observability 的组合。

强中心也可以完整获胜，前提是它确实获得了所有相关 owner 的合法委托，并能访问权威目标状态；共享数据库或中央 workflow 本身不是问题，伪造 owner 权威才是问题。

**稳定 residual 主要来自不可观测、不可代行权威、对象语义不一致、真实采用的私有性和因果不可识别。**这些缺口不会因为再增加一个 Effect receipt、hash 或 event envelope 而消失。

因而，当前没有充分理由预设通爻需要发明专用 Effect 协议。更有价值的研究产物是：可证伪的分层评估、owner-scoped ledger、typed-DAG 语义和不可辨识性边界。

以下是形式重建与实验方案，不是已经运行过的实测结果；我不会为尚未执行的现场实验虚构数字。

二、先纠正一个本体错误：五层不是五种互斥“物质”

一个对象在不同关系中可以同时扮演多个角色：

某个容器镜像被写入生产集群，是生产基础设施域中的 Effect。

该镜像开始承载真实业务流量，是产品团队相对于此次发布的 Adoption，同时也是流量控制域中的另一个 Effect。

产品 owner 点击正式验收，是合同或项目管理域中的 Effect，但相对于交付物，它是 Acceptance。

款项到账是银行账本中的 Effect，同时是合同义务上的 Settlement。

所以五个词不是一套互斥的世界本体，而是：

某个事实或制度行为，在指定 episode、指定目标、指定 owner 和指定 qualification rule 中所扮演的角色。

这也是为什么固定的：

Attempt → Effect → Adoption → Acceptance → Settlement

必然会失败。真实任务可能出现：

安全审批在 Attempt 前发生；

Adoption 在正式 Acceptance 前发生；

预付款 Settlement 在 Effect 前发生；

一个 owner 接受，另一个 owner 拒绝；

技术 Acceptance 已有，但长期性能 Acceptance 要在 Adoption 后才能发生；

Effect 已发生，但随后又被 compensation；

新版本 supersede 旧版本，使旧 Acceptance 仍是历史事实，但不再覆盖当前对象。

三、形式对象
3.1 Episode

定义一个 episode：

e=⟨Q
v
, O, P, Γ, Π, T⟩

其中：

Q
v
：目标及其版本；

O：对象集合；

P：相关 principal/owner；

Γ：任务特定的 typed DAG；

Π：权限、验收、采用与结算规则版本；

T：有效时间窗口。

3.2 Exact object reference

仅有 artifact hash 不足以识别任务对象。建议至少使用：

ObjectRef=⟨authority, domain, tenant/namespace, localID, revision/digest, schemaVersion, policyVersion, validTime⟩

同样一组 bytes：

部署在 staging 和 production，不是同一个对象；

附着于 CNC-17 和 CNC-71，不是同一个对象；

用在旧合同里程碑和新合同里程碑，不是同一个结算对象；

同一个模型权重配不同 prompt、corpus、ACL，不是同一个 AI 服务版本。

Hash 可以证明字节相等，却不能单独证明现实指向、部署位置、owner、政策版本或义务归属。

3.3 Claim 与 Evidence 分离

定义一条 claim：

c=⟨episode, role, issuer, authorityScope, objectRef, predicate, validTime, observedAt, evidenceRefs, predecessors, status⟩

其中 role 可以是 Attempt、Effect、Adoption、Acceptance 或 Settlement。

但必须另有 evidence store。消息、日志、trace、传感器记录、receipt、hash、签名和 readback 都是 evidence，不自动升级成 claim，更不自动升级成被验证的现实事实。

建议区分：

X
∗
：现实中的事实或有效制度行为；

X
^
：系统报告的 claim；

W
X
	​

：支持或反驳该 claim 的 evidence。

实验中的 precision/recall 比较的是 
X
^
 与 X
∗
，不是比较“系统有没有写一条日志”。

四、五种角色的独立定义
角色	独立定义	主要权威来源	不自动意味着
Attempt	某 actor 对 exact operation 实际越过执行边界；授权是否合法是另一个属性	执行端、操作审计、调用入口	Effect、合法性、完成
Effect	exact target domain 的状态实际发生了满足指定 predicate 的变化	目标域 owner、权威 readback、独立现实测量	Adoption、Acceptance、Settlement
Adoption	指定 adopter 在约定时间窗内把 exact object/effect 纳入实际运行或行为	使用域、MES、流量、业务行为、adopter owner	满意、验收、付款
Acceptance	具有相应 authority 的 owner 针对 exact object/version 和 criterion version 作出的规范性接受行为	owner 本人或其合法委托系统	Effect 真、实际采用、已结算
Settlement	指定义务在某一结算制度下被部分或全部履行、转移或最终解除	escrow、支付机构、银行或法定账本	Effect、Acceptance、采用、款项已最终到达受益人

还应区分 raw occurrence 与 episode-qualified occurrence：

Q
X
	​

(e)=X
raw
	​

∧ExactBinding∧CurrentVersion∧ValidTime∧ApplicablePolicy

对 Attempt、Acceptance、Settlement，还通常需要 Authority 条件。

例如：

未授权人员确实改变了机器参数：RawEffect=true，但 QualifiedEffect=false。

产品 owner 接受了 v4，但当前待结算对象是 v5：Acceptance act 存在，当前版本的 QualifiedAcceptance 不存在。

支付机构发生了一笔款项移动，但义务 ID 错误：Raw settlement event 存在，QualifiedSettlement 不存在。

历史事实不能被事后抹掉。Rollback 或退款应产生新的 compensation/reversal 节点，而不是把原 Effect 或 Settlement 从历史中删除。

五、非蕴含关系

在没有 task-specific typed rule 的情况下，五层之间不存在普遍蕴含。

5.1 Delivered、ACK、hash、event 和 workflow green

CloudEvents 将 event 定义为“表达某一 occurrence 及其上下文的数据记录”；一个 occurrence 可能产生多个 event，event 通过 message 传输，consumer 收到后才可能执行新的逻辑。source + id 可以帮助 consumer 识别重复 event，但这仍只是事件身份和传输语义。
GitHub
+1

因此：

Delivered

⇒Attempt
ACK

⇒Effect
HashExists

⇒Effect
ReceiptExists

⇒Acceptance
WorkflowGreen

⇒Effect

后一个反例甚至不需要故障：AWS Step Functions 的 Pass state 可以在“不执行任何工作”的情况下产生输出并正常结束。
AWS 文档

5.2 Attempt 不蕴含 Effect

调用可能：

被目标拒绝；

命中错误环境；

因 CAS/precondition 失败而没有应用；

部分执行后被目标自身回滚；

物理执行未接触正确资产；

实际完成，但响应在返回前丢失。

因此：

A

⇒E

反方向也不成立。目标状态可能由另一个 actor、自治 controller、人工操作或早先请求改变：

E

⇒A
i
	​


真正需要单独判断的是：

Cause(A
i
	​

,E
j
	​

)

而不是从时间接近或 trace 路径中自动推导因果。

5.3 Effect 不蕴含 Adoption

软件部署成功但 feature flag 关闭；

模型已安装但无人把它纳入工作流；

机器已修好但 MES 仍把它标为停机；

文件已生成但业务人员继续使用旧版本。

E

⇒D
5.4 Adoption 与 Acceptance 双向不蕴含

用户可能已经在用一个尚未正式验收的工具：

D

⇒K

owner 也可能提前验收、错误验收、接受设计而非运行结果，或者接受后一直没有采用：

K

⇒D

美国联邦采购规则本身就把 acceptance 定义为有权机关对合同质量和数量符合性的确认，并明确 acceptance 可能发生在交付前、交付时或交付后；其责任属于 contracting officer 或被正式指派的机关。由此也能看出，“award”“approved”“vendor ACK”和“performance acceptance”必须是不同类型。
采购网

5.5 Acceptance 与 Settlement 双向不蕴含

接受后可能因付款争议、预算冻结或支付失败而未结算；

预付款、押金或误付款可能在 Effect 和 Acceptance 前发生；

Settlement 可能只到 PSP，尚未 payout 给 merchant；

payment authorization、capture、sent-for-settle、settled、payout 和法律 finality 是不同阶段。

Adyen 明确区分 capture、SentForSettle 和 Settled，并说明“Settled”不等于款项已经 payout 给商户；ECB 对 final settlement 的定义还要求无条件、可执行且不可撤销。
Adyen 文档
+1

因此：

K

⇒S,S

⇒K
六、一个稳定的不可辨识性下界

设 controller 只能看到：

O
c
	​

={message, deliveryACK, receipt, hash, eventLog, workflowState}

构造两个世界：

W
1
	​

：消息送达，target write 成功，现实 Effect 已发生；

W
2
	​

：消息送达，target write 因版本冲突被拒绝，或者写入了错误 tenant，现实目标 Effect 没有发生。

让两边产生完全相同的 ACK、日志、receipt 和 workflow green。

任何只依赖 O
c
	​

 的判定器，在两个世界中的输出分布都相同。因此：

若它报告 Effect，在 W
2
	​

 中产生 false positive；

若它不报告 Effect，在 W
1
	​

 中产生 false negative。

所以，在没有新增 target-domain readback、独立现实测量或 owner act 的情况下，不存在同时获得零 false positive 和零 false negative 的判定器。

对 Adoption 和 Acceptance 也有同样结论：

两个组织可能有完全相同的部署和使用日志，但一个 owner 已接受、另一个 owner 明确保留异议；

如果 owner 的判断没有被披露，也没有合法委托给 controller，controller 无法从技术 trace 中推导出 Acceptance。

这是 G6 的稳定边界。它不是“模型还不够聪明”，也不是“协议字段不够多”，而是输入信息与 authority 本身不足。

七、失败分类
类别	典型错误	正确处理
控制面替代目标域	把 ACK、job completed、workflow green 当 Effect	查询 target-domain current state
对象/版本漂移	接受了正确 hash，但属于错误 tenant、机器或里程碑	绑定完整 ObjectRef 和 criterion version
owner/authority 替代	controller、vendor 或模型代 buyer/security owner 验收	只接受 owner 或合法 delegate 的 act
readback 失真	desired state、缓存、旧 generation 被当成 current state	检查 authority、freshness、generation、valid time
重复与 replay	retry 再次付款、再次发信、再次执行物理动作	target-side idempotency、消费账本、read-before-retry
crash ambiguity	Effect 已发生但本地未记账，恢复后盲目重试	恢复后先权威 readback，再决定重试
类型混淆	security approval、award、delivery receipt 被映射为 performance acceptance	acceptance type 必须显式
拓扑线性化	强迫所有任务按五级顺序前进	task-specific typed DAG
因果误归属	看到 trace 或时间先后就认定某 Attempt 导致 Effect	操作 token、排他窗口、干预或保留 Unknown
Adoption proxy 错误	发放账号、一次登录、测试流量被当成采用	owner 定义的时间窗、业务使用和阈值
结算阶段坍缩	payment sent、capture、settled、payout、finality 混成一个状态	使用 scheme-specific settlement subgraph
compensation 幻觉	把 compensation 当作历史 Effect 从未发生	保留原 Effect，新增 reversal/compensation 节点
八、现有技术的真实覆盖
8.1 Transaction 与 transactional outbox

Transactional outbox 解决的是本地数据库写入和事件发送之间的 dual-write 原子性问题。它可以防止“数据库提交了但通知没有产生”或“数据库回滚了却发出通知”等不一致；但官方文档也明确提醒 event relay 可能发送重复消息，consumer 仍需实现 idempotency。
AWS 文档

覆盖：

本地 Attempt/request 状态与 outbox event 一致；

通知最终可达；

有序发布与恢复。

不覆盖：

consumer 是否真正改变目标现实；

改变的是不是正确对象；

downstream side effect 是否重复；

Adoption、Acceptance、Settlement。

结论：必要但只覆盖控制面的一小段。

8.2 Durable workflow 与 saga

Durable workflow 很适合保存执行历史、等待、重试、人工 task 和长事务。Saga 在不能使用分布式 ACID 时提供 eventual consistency 与 compensation；但 compensation 可能不存在、不可逆或重复执行，因此 forward action 和 compensation 都需要 idempotency。Temporal 的文档甚至以“信用卡已扣款，但 Activity 尚未返回成功”为典型歧义窗口。
Temporal 文档

某些 workflow 产品提供 exactly-once workflow execution；这描述的是其 state/task 执行模型，不等于所有外部现实 side effect 都具有全局 exactly-once 语义。
AWS 文档

结论：workflow 是恢复与协调骨架，不是 Effect oracle。

8.3 Event sourcing 与 CloudEvents

Event sourcing 提供应用内状态变更历史、审计和重放，但官方指导也指出：

冲突 event 可能使最终状态与现实不符；

projection 可能因为 eventual consistency 而不是当前状态；

replay 外部系统更新时可能重新触发 side effect。
AWS 文档

CloudEvents 主要解决 event 描述和跨系统互操作，而不是证明 occurrence 的现实真实性或 owner acceptance。
GitHub

结论：优秀的 evidence/provenance transport，不是现实真值层。

8.4 Target-domain readback 与 reconciliation

这是机器可读域中确认 Effect 的最强成熟方法。

readback 至少应检查：

来源是否属于 target owner；

返回的是 desired state 还是 observed state；

exact object/version；

freshness/generation；

是否存在 projection lag；

当前状态是否已经被其他 actor supersede 或 compensate。

Kubernetes 的 observedGeneration 就是典型 freshness 防线：如果 status condition 基于 generation 9，而当前 metadata generation 已经是 12，该状态明确是过期的。Terraform 的 refresh 则通过 provider 报告的资源当前状态来更新本地认知并发现 drift。
Kubernetes
+1

结论：对可权威查询的数字目标域，readback 可以完整覆盖 Effect；对不可传感的物理状态、私有行为和主观判断，只能部分覆盖。

8.5 Observability 与 SRE

OpenTelemetry 的 trace、metric、log 和 baggage 可以恢复请求路径、运行指标和跨服务相关性；context propagation 能建立请求级 lineage。
OpenTelemetry
+1

但 trace correlation 不应被提升为干预意义上的因果证明。W3C PROV 的形式语义也明确指出，仅有 generation/use 链并不足以可靠推导 derivation，相关关系必须被明确断言。
W3C

Google SRE 对周期任务的建议很直接：double launch 可能难以甚至无法撤销，任务 owner 应独立监控任务的实际 effect，系统应倾向 fail closed。
Google SRE

结论：Observability 提供侦测、相关性和恢复线索，不提供 owner authority。

8.6 Human acceptance、CLM、e-sign 和 case management

只要满足以下条件，成熟的人类制度已经可以完整构成 Acceptance：

actor 确实拥有该 acceptance type 的 authority；

act 绑定 exact object/version；

criterion 与 policy version 明确；

条件、reservation、partial acceptance 和 objection 被保留；

新版本自动要求重新确认或显式迁移。

人类并非必须介入每一次验收。owner 可以合法授权自动测试、policy engine 或控制系统代表其作出特定范围的 acceptance；关键是委托关系，而不是“必须人工点按钮”。

结论：这是独立 owner Acceptance 的现成熟解，代价是等待、人工与治理成本。

8.7 Escrow 与 settlement rails

Escrow、支付服务、银行账本和合同系统能够完整解决其自身 scheme 内的资金保留、条件释放和结算状态；但条件输入本身仍需要可靠的 Effect/Acceptance claim。

结论：可以完整覆盖 Settlement，但不能反向证明技术 Effect。

8.8 强中心

强中心在以下情况下可以完整获胜：

所有 relevant owner 已合法授予 authority；

所有目标域都可由中心权威 readback；

对象和 policy 版本统一；

中心拥有防重、恢复和结算权限；

中心的 acceptance act 在制度上确实绑定各 principal。

相反，若 acceptance authority 仍属于独立 buyer、监管者、生产 owner 或数据 owner，中心数据库中的 accepted=true 只是中心自己的 assertion。

结论：强中心的边界由真实 authority 和 observability 决定，不由架构图是否中心化决定。

8.9 通用模型

通用模型可以：

将自然语言 SOP 映射成 typed DAG 草案；

选择 readback 工具；

检查对象和版本不一致；

汇总 evidence；

判断何时应查询、重试或升级人工；

减少人工验收材料整理成本。

但模型调用工具时，真正的操作由外部应用或 server-side tool 执行；模型本身既不是 target state，也不是 owner authority。
Claude Platform Docs

结论：模型适合 planner、adapter 和 exception handler，不应成为 Effect、Acceptance 或 Settlement 的根信任源。

九、最强的“无新协议”端到端组合

不需要发明新的网络协议。普通数据库、现有 event envelope、durable workflow、target API、监控、CLM/e-sign 和支付系统即可组成完整方案。

9.1 最小结构

Exact operation contract

每次操作绑定 episode、object/version、target、precondition、expected transition、idempotency key 和 policy version。

Target-side safety

在目标端使用 CAS、唯一 operation key、幂等记录或本地事务。不能只在 workflow 层去重。

Transactional outbox

将本地 operation record 与待发布 event 放入同一事务。

Durable workflow

管理调用、等待、人工审批、timeout、补偿和升级，但不直接把 Activity success 映射为 Effect。

Authoritative readback/reconciliation

对每个可能模糊的外部 Effect，在成功响应后、timeout 后和恢复后重新读取目标当前状态。

Independent owner ledgers

每个 owner 只能写入自己具有 authority 的 claim。这里的 ledger 可以只是同一 PostgreSQL 中受 RBAC 控制的逻辑表，不要求区块链或分布式数据库。

Acceptance and adoption gates

Adoption 根据 owner 预先定义的真实使用条件；Acceptance 根据指定 owner、type 和 criterion version。

Settlement reconciliation

webhook 只是通知；结算必须通过 payment/escrow 的 authoritative query 核对 exact obligation、金额、party 和 finality。

Observability and provenance

保存 traces、metrics、logs、readback、签名和人工决定，但 evidence 与 qualified claim 分开。

Derived episode view

“完成”只是一个版本化 policy 对各 ledger current head 的查询结果：

Done
e
	​

(t)=ϕ
e
	​

(Head(L
A
	​

),Head(L
E
	​

),Head(L
D
p
	​

),Head(L
K
p
	​

),Head(L
S
	​

))

Done 不是新的权威事实，更不能覆盖底层 owner disagreement。

9.2 恢复规则

在 crash after effect, before local commit 之类的窗口中：

本地没有 success record，不等于 Effect 没有发生。

恢复后先按 operation key、object/version 查询 target。

若 exact Effect 已存在，记录 RecoveredEffect，不得重试真实 side effect。

若确认不存在且 operation 幂等，可以重试。

若 target 无权威 readback，返回 Unknown/ManualReconciliation，不能猜。

若 Effect version 已改变，所有绑定旧版本的 Adoption/Acceptance 必须保持历史记录，并按 policy 决定是否 reopen。

对 Settlement 独立查询 provider current state，禁止仅凭旧 webhook 重新释放资金。

十、六个必测反例
反例	表面 evidence	隐藏现实	正确输出
Delivered-but-no-effect	broker ACK、consumer 200、workflow green	target CAS 失败，或写入 staging 而非 production	Attempt 可能成立；QualifiedEffect=false
Effect-without-adoption	exact version 已部署并健康	feature flag 关闭、零真实流量、机器未被 MES 放行	Effect=true；Adoption=false
Wrong-object acceptance	有效 owner 签名、report hash 正确	report 未绑定正确 tenant、机器序列号或当前 revision	Raw acceptance act=true；QualifiedAcceptance=false
Award-vs-performance acceptance	合同 award、PO approved、vendor ACK	尚未交付，或交付性能不合格	Commitment/Award=true；PerformanceAcceptance=false
Crash-between-effect-and-acceptance	target 已改变，workflow 本地无完成记录	Effect 真实存在，acceptance task 尚未创建	readback 恢复 Effect；不得盲目重试；Acceptance=absent
Receipt replay	旧 receipt 签名有效，artifact hash 相同	receipt 属于旧 episode/旧义务，已消费	replay/reject；不得新增 Acceptance 或 Settlement

Receipt 的安全绑定至少需要：

episode ID；

exact object/version；

acceptance type；

owner 和 authority scope；

obligation ID；

audience；

validity window；

one-time consumption/idempotency key；

当前 policy version。

CloudEvents 的 source + id 可以帮助识别重复 event，但若攻击者把旧 receipt 包装进一个新 event ID，只有 domain-level obligation consumption ledger 才能阻止重复结算。
GitHub

十一、三个真实任务
任务一：外包团队发布生产计费服务
Exact task

将 OCI digest d7 和 configuration revision c12 部署到：

cluster：prod-us

namespace：billing

service：invoice-api

canary：10%

目标：30 分钟内错误率、P95 latency 和业务正确性满足预注册条件。

Typed DAG
SecurityApproval(plan v3)
        ↓
Attempt(deploy d7/c12)
        ↓
Effect(prod-us/billing actually runs d7/c12)
        ↓
Adoption(real production traffic reaches d7)
        ├── SREAcceptance(canary/SLO)
        └── ProductAcceptance(invoice correctness)
                    ↓
Settlement(contract milestone)

其中 SecurityApproval 是 Effect 前的 Acceptance，但不是运行结果 Acceptance。

Ground truth

Attempt：API server/runner 收到 exact operation；

Effect：Kubernetes observed generation、running image digest、service mesh route 和外部 probe 一致；

Adoption：真实计费 transaction 由新版本处理，而不是 synthetic traffic；

Acceptance：SRE 与 product owner 分别签署自己的 acceptance type；

Settlement：contractor milestone 在两个必要 Acceptance 后释放。

关键故障

wrong cluster；

stale status；

same tag、different digest；

workflow Pass/no-op；

deploy 成功后 crash；

canary 部署但零流量；

旧 release acceptance replay；

另一个 SRE 同时改写流量，造成因果误归属。

Canary 需要同时比较 release candidate 与 control，并以真实生产流量评估，而不是只看“部署成功”。Google SRE 的 canary 方法也是通过小比例真实流量、版本分组指标和明确 evaluation process 来判断变化是否良好。
Google SRE

任务二：金属制造厂 CNC-17 主轴维修与重新放行
Exact task

供应商对资产：

asset ID：CNC-17

spindle serial：SP-4472

parameter package：P9

test-piece drawing：TP-31 v4

完成更换、校准，并达到 runout、振动、尺寸公差和连续生产时间要求。

Typed DAG
SafetyPermit + LockoutVerification
                 ↓
Attempt(repair CNC-17/SP-4472)
                 ↓
Effect(physical replacement + calibration)
                 ↓
QA Acceptance(test piece TP-31 v4)
                 ↓
Adoption(MES releases machine + real batch scheduled)
                 ↓
ProductionPerformanceAcceptance(7-day window)
                 ↓
Final Settlement

合同还可以包含：

AdvanceSettlement(30%) → Attempt

因此 Settlement 并非总在最后。

Ground truth

Attempt：维修人员进入 LOTO 区域并开始指定 work order；

Effect：资产序列号、PLC 参数、独立 runout/vibration measurement 和 CMMS 记录一致；

Adoption：MES 真正解除停机状态并安排生产批次；

Acceptance：

maintenance owner 接受维修完成；

QA 接受 test piece；

production owner 接受 7 天运行性能；

Settlement：70% 完工付款，20% 或其他比例 holdback 后释放。

关键故障

修了 CNC-71，却在 CNC-17 工单下上传报告；

复制旧 vibration trace；

维修完成但 QA 未放行；

QA 放行但生产继续停机；

vendor 完成维修后系统 crash，workflow 重发 work order；

maintenance acceptance 被错误当成 production-performance acceptance。

这是最能检验“目标域 readback 不是免费 API”的任务：部分现实只能由传感器、独立测量、人类检验和实际生产窗口共同建立。

任务三：企业采购并上线 AI 知识助手
Exact task

供应商在指定生产 tenant 中上线：

model revision：m8

system prompt：p14

corpus snapshot：k2026-07-20

ACL policy：acl9

SSO group：procurement-prod

held-out evaluation set：eval-v5

Typed DAG
Award / ContractFormation
        ├── AdvanceSettlement
        └── Attempt(deploy exact AI configuration)
                    ↓
Effect(prod tenant contains m8/p14/k.../acl9)
        ├── SecurityAcceptance
        └── DataOwnerAcceptance
                    ↓
Adoption(real procurement workflows use it)
                    ↓
BusinessPerformanceAcceptance(held-out period)
                    ↓
Final Settlement

Award 是合同形成，不是 performance acceptance。

Ground truth

Attempt：供应商确实执行 production deployment；

Effect：目标 tenant 对 exact model/prompt/corpus/ACL 的权威查询；

Adoption：员工在获准采购流程中真实使用，不把 license assignment、一次登录或 vendor demo 当成采用；

Acceptance：

security owner 接受数据边界；

knowledge/data owner 接受 corpus 与权限；

department owner 接受工作流适配；

business owner 在 held-out 时间窗接受效果；

Settlement：订阅费或 milestone 按指定 acceptance graph 释放。

关键故障

staging demo 被报告为 production Effect；

模型版本正确但 ACL 错误；

license 已发放但无人使用；

security approval 被当作业务 performance acceptance；

award email 被当成最终验收；

旧 pilot receipt 触发正式合同付款；

使用量提高，但同时发生组织培训，模型被错误归因为全部绩效提升。

这个任务也最适合比较通用模型：LLM 可以整理 evidence 和查询工具，但不能代 security owner、department owner 或付款方作出 Acceptance。

十二、Independent owner ledgers

这里的 ledger 是逻辑上的独立写权限和可追溯 current head，不等于必须部署五条区块链。

Ledger	唯一可产生权威 claim 的主体	内容
L
A
	​

	executor 或执行入口	Attempt、actor、operation、authorization evidence
L
E
	​

	target owner/readback adapter	before/after、current version、freshness、Effect status
L
D
p
	​

	adopter p 或其业务系统	实际使用、release、流量、时间窗、Adoption
L
K
p,k
	​

	owner p，acceptance type k	Accept、Reject、Conditional、Reservation、Revoke、Dispute
L
S
	​

	escrow/payment/settlement authority	obligation、amount、phase、finality、reversal

规则：

Controller 可以请求和缓存，但不能以 owner 身份写入 L
K
p,k
	​

。

同一个中心数据库可以承载所有 ledger，只要 write authority 真实分离。

每条 claim 必须绑定相同的 episode/object/version/obligation join key。

owner disagreement 必须原样保留。

aggregate acceptance 是版本化 policy 的派生结果，不能覆盖底层 owner claim。

supersession、revocation 和 dispute 产生新节点，不修改历史。

目标域恢复必须读取 L
E
	​

 的权威 current head，而不是仅 replay controller 自己的 event store。

十三、Held-out typed-DAG 实验
13.1 公平基线
基线	内容
B0 Receipt-Ladder	ACK/hash/workflow green + 固定五级 ladder
B1 Mature Infra	transaction/outbox + durable workflow/saga + event sourcing/CloudEvents + observability
B2 Readback Stack	B1 + exact identity/version + target readback + reconciliation + target-side idempotency
B3 Owner-Complete Composition	B2 + independent owner ledgers + acceptance system + settlement finality
B4 Human Institution	SOP、ticket、inspection、CLM/e-sign、人工 reconciliation、普通支付
B5 Strong Center	与 B3 相同能力，但集中决策；分“合法全委托”和“authority 仍独立”两个条件
B6 General Model	分 LLM-only 和 LLM+B3；模型可选工具、整理 evidence，但不能绕过 owner gate

公平性要求：

各基线获得相同的目标 API、原始 evidence 和执行权限；

不给某个方案隐藏的免费 oracle；

不把 owner authority 私下赠送给 strong center 或 LLM；

“合法全委托”作为独立实验条件，允许 strong center 正面获胜；

所有系统都可以输出 Unknown；

Acceptance criteria、object version 和 value function 在 episode 前冻结；

Gold truth 对运行系统不可见。

13.2 两条实验轨道
轨道 A：给定 typed DAG

这是 G6 的主实验。系统收到明确的 DAG、owner、criterion 和权限，测试：

是否正确执行；

是否错误跨层升级；

是否在 crash 后恢复；

是否保留 owner disagreement；

是否处理新拓扑。

这样不会把 G2/G5 中“如何从自然语言形成任务和授权对象”的难题偷混进 G6。

轨道 B：从合同/SOP 构建 DAG

这是扩展实验，用来比较：

人工建模；

rule/template；

通用模型；

通用模型加确定性 validator。

轨道 B 的错误必须与轨道 A 的运行时错误分开报告。

13.3 Held-out topology

开发集可包含 12 类 graph motif，测试集完全保留至少 6 类未见组合：

Effect 前的 security Acceptance；

Adoption 在 performance Acceptance 前；

Advance Settlement 在 Effect 前，holdback 在后；

多 owner 全部同意；

k-of-n owner 接受；

一个 owner Accept、另一个 Reject；

partial object acceptance；

Effect compensation 后 reopen；

old version accepted，new version supersede；

alternative Effect path；

staged adoption；

settlement split；

disputed acceptance；

target state Unknown；

owner revocation；

adoption window 尚未结束；

parallel effects merge；

exact-object migration。

Held-out 不应只是换字段名，而应真正改变：

节点顺序；

edge type；

owner aggregation；

settlement placement；

supersession 和 reopening 规则。

系统需要输出：

qualified nodes；

typed edges；

current owner heads；

Unknown/Reject/Defer；

task policy 派生结果。

同时报告 node F1、typed-edge F1、invalid-completion rate 和 topology generalization gap。

13.4 Fault-injection 设计

参考受控基准可以采用：

3 个任务；

6 个指定反例；

clean-success 与 genuinely-unidentifiable 两类 control；

4 个 modifier：

单一 actor；

并发合法 actor；

指定 crash window；

object/version supersession。

这构成：

3×8×4=96

个核心实验条件。每个条件至少多次独立运行；最终样本量由 pilot variance 和 power analysis 决定。

物理制造任务中的危险故障应在真实控制系统连接的测试工位或安全 test cell 注入，再用少量无破坏 live episode 验证外部有效性，不能为了“真实”而重复制造危险生产事故。

重点 crash point：

target Effect 前；

Effect 后、响应前；

Effect 后、本地 ledger commit 前；

Effect ledger 后、Acceptance task 前；

Acceptance 后、Settlement request 前；

Settlement 已发生、webhook 前；

receipt 消费后、消费记录 commit 前。

十四、指标
14.1 五层 precision/recall

对每一层 t∈{A,E,D,K,S}：

Precision
t
	​

=
TP
t
	​

+FP
t
	​

TP
t
	​

	​

Recall
t
	​

=
TP
t
	​

+FN
t
	​

TP
t
	​

	​


正例必须 exact match：

⟨episode, role, owner, object, version, predicate/type, validTime, finality⟩

错误对象或错误版本同时计为：

一个 false positive；

对正确对象的一个 false negative。

需同时报告：

micro/macro precision/recall；

每个 task 和 owner 的分层结果；

calibration；

coverage；

selective risk；

Unknown 的正确率。

对故意设置成不可识别的 episode，强行输出 True 或 False 是错误，Unknown 才是正确结果。

14.2 Duplicate Effect
DER=
effect-eligible episodes
unintended additional real target transitions
	​


另报 severity-weighted duplicate loss，因为：

重复 GET 几乎无损；

重复付款、重复群发、重复物理加工可能不可恢复。

14.3 Wrong object/version

报告：

wrong target；

wrong tenant/namespace；

wrong asset；

stale revision；

policy/criterion version mismatch；

hash-correct-but-context-wrong。

14.4 Causal attribution

把 Cause(A_i,E_j) 作为独立 typed edge，报告 precision/recall。

Gold causal evidence优先级：

target state 内持久化 operation token；

target audit 能唯一绑定 write；

排他执行窗口和无竞争 writer；

随机 withholding/intervention；

仅 trace 或时间相关。

在并发 actor 无法排除时，应允许 Effect=true, Cause=Unknown。

14.5 Recovery authoritative readback

报告：

crash 后首次决策前是否完成权威 readback；

reconstructed current head accuracy；

unsafe retry rate；

recovery convergence latency；

stale-read acceptance rate；

Effect 已存在却被重复执行的比例；

Effect 不存在却被误判已完成的比例。

14.6 Owner acceptance

分三层测：

Act accuracy：是否正确报告 owner 实际作出的 act；

Qualified acceptance accuracy：authority、object/version、type、criterion 是否全部有效；

Substantive error：在存在客观验收条件时，owner/system 是否接受了实际不符合条件的对象。

另报：

unauthorized acceptance；

owner disagreement preservation；

aggregate status 覆盖异议的比例；

acceptance reopen/revocation latency；

wrong acceptance type。

14.7 等待、人工和治理成本

至少包括：

各层 p50/p95 latency；

owner 等待时间；

人工分钟数；

owner interruption 次数；

readback/API 查询数；

exception case 数；

policy/schema 修改次数；

dispute 数；

资金锁定时间；

跨组织协调成本。

14.8 净价值

在多 principal 情况下，应先报告 owner-specific net value：

NV
p
	​

=V
p
	​

(realized qualified graph)−C
exec,p
	​

−C
verify,p
	​

−C
human,p
	​

−C
wait,p
	​

−C
govern,p
	​

−L
p
	​

(duplicate, wrong object, replay, false acceptance)

除非各 principal 已授权一个聚合规则，否则不应私自把不同 owner 的 NV
p
	​

 汇成单一“社会总价值”。

十五、预注册假设与赢者判定

这些是实验前假设，不是结果。

B0 Receipt-Ladder
在正常路径上可能 recall 很高，但在六个反例中会出现系统性 false Effect、false Acceptance 和 duplicate Settlement。

B1 Mature Infra
会显著减少消息丢失、workflow 中断和本地状态不一致，但不会消除 delivered-but-no-effect、effect-without-adoption 和 owner substitution。

B2 Readback Stack
在具有权威机器接口的数字域中，应显著提高 Effect precision/recall，并降低 crash 后重复 Effect；但不能自行解决 Adoption、Acceptance 和结算 authority。

B3 Owner-Complete Composition
是最可能完整解决端到端 G6 的现有组合，同时会增加 owner waiting、人工和治理成本。

B4 Human Institution
在语义上可能与 B3 一样可靠，甚至在物理和主观验收上更强，但 latency、人工成本和可扩展性较差。

B5 Strong Center
在合法全委托条件下可以持平或击败 B3；若 authority 仍独立，中心代签应被计为 unauthorized acceptance，而不是架构胜利。

B6 General Model
LLM+B3 可能降低材料整理、异常分流和 human minutes；LLM-only 不应在高风险层成为最终判定器。其可靠性来自 readback、owner act 和 settlement rail，而不是模型自己“理解了现实”。

胜者不能只看 recall。至少应满足：

unsafe false Effect 不超过任务预注册容忍度；

unauthorized Acceptance 和 double Settlement 作为零容忍严重缺陷；

owner disagreement 不被抹平；

Unknown 使用合理；

端到端 net value 优于成熟人工基线；

不依赖评估中隐藏的免费 oracle 或代签 authority。

十六、哪些已被完整解决，哪些只是部分覆盖
16.1 现成组合可以完整解决
封闭数字域

当满足以下条件时，成熟组合足够：

exact object/version 可寻址；

target 提供权威且带 freshness 的 readback；

operation 支持 idempotency/CAS；

Adoption 有可操作定义和真实 usage source；

owner Acceptance 可通过明确 authority act 获得；

settlement provider 可被权威查询；

crash 后可以重新读取所有 current heads。

在这个条件下，普通 workflow、数据库、readback adapter、CLM/e-sign 和支付系统已经可以完整解决。专用 Effect 协议不是必要条件。

真正单一 authority 的组织

若一个中心确实拥有：

目标域；

adopter 决策；
-验收权；

结算权；

那么强中心完全可以是最佳方案。把系统强行分布式反而会增加成本。

跨组织但接口完备

不同 owner 可以把各自 ledger 托管在不同系统，也可以共用一个平台。只要 exact binding、write authority、readback 和 dispute 保真，现有身份、签名、workflow、合同和支付基础设施可以完成闭环。

16.2 只能部分覆盖
物理现实缺少充分 oracle

传感器只能观察局部，目标域可能需要：

独立检验；

多传感器交叉验证；

人工 inspection；

实际运行窗口；

抽样与统计推断。

Adoption 是私有或模糊行为

“组织真正采用了某工具”可能不能由：

license assignment；

一次登录；

管理者口头宣布；

强制培训出席；

充分判断。必须由 owner 定义 adoption criterion，否则 precision/recall 本身都没有稳定标签。

Acceptance 是主观或争议性的

系统只能忠实记录 owner 的 act、reservation 和 dispute，不能通过技术证据消灭真实价值冲突。

长期绩效与因果归属

效果与组织培训、季节变化、其他软件发布和人员变化并发时，observability 可以提供相关性，但不必然建立因果。需要随机化、对照、分阶段 rollout 或诚实保留 Unknown。

十七、稳定 residual

以下 residual 在架构和产品更换后仍会存在：

不可观测性 residual
target reality 没有权威 readback，或 readback 本身只是旧缓存、desired state、自我报告。

Authority residual
controller、workflow 或模型不能凭技术能力创造另一个 principal 的 Acceptance。

Semantic identity residual
两个系统可能都提供合法 ID 和 hash，却对“对象”“版本”“完成”和“接受”使用不同语义。

Adoption privacy residual
真实采用可能存在于私有行为和组织实践中，owner 可以拒绝披露。

Causal residual
并发 actor、环境变化和反馈回路使 Attempt→Effect 或 Adoption→Value 的归属无法仅靠 trace 确定。

Settlement/legal residual
finality、chargeback、欺诈、争议和义务解除取决于具体 payment scheme、合同和司法制度。

verification-cost residual
更强 readback、更多 owner acceptance 和更严格因果验证会增加等待、人工和资金锁定；不存在免费的全知 oracle。

新的 claim envelope 或 Effect protocol 可以降低跨系统交换成本，但不能消除这些 residual。

十八、对通爻研究路线的最终判断

G6 最强的零假设应当是：

在对象和版本精确绑定、目标域可权威 readback、owner authority 可独立表达、settlement 可查询的范围内，成熟组合已经完整解决；没有额外专用 Effect 协议的必要性。

通爻若要证明新机制的独立价值，至少必须在公平实验中证明：

B3 的成熟组合仍无法表示或迁移某个必要语义；

缺口不是目标域不披露、owner 不授权或实验偷偷需要免费 oracle；

新机制提高五层 precision/recall 或降低成本；

不通过把 Unknown 误报为 Effect、把 aggregate green 冒充 Acceptance 来获得表面 recall；

在 held-out typed DAG、crash、replay、wrong-object 和跨 owner disagreement 中仍保持语义；

生命周期净价值超过 adapter、人工制度或强中心方案。

否则，最可靠的研究结果不是“又发现了一个 Effect 协议缺口”，而是：

Effect 的核心问题是目标域权威 readback；Adoption 的核心问题是行为与 owner 定义；Acceptance 的核心问题是不可代签权威；Settlement 的核心问题是义务与 finality。消息、workflow 和 event log 负责把这些事实带回来，却不能替它们发生。

