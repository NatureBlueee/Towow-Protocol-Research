# G5 ChatGPT Pro return

- Conversation: https://chatgpt.com/c/6a69e303-9b54-83ea-8772-9aadc3ec9377
- Captured: 2026-07-29
- Status: external candidate evidence; not independently validated
- Preservation note: assistant visible text transcribed verbatim from the signed-in in-app browser; page structure and link previews are not embedded here.

---

G5 独立研究报告：权威、规范与可追责承诺

研究结论日期：2026 年 7 月 29 日

先说明证据状态：下面给出了完整的问题重建、现成技术比较、可执行基线、指标和反例集；但没有伪造尚未运行的实验数字。文中“预期”均是需要由实验推翻或确认的假设，不是实测结果。

一、核心结论

G5 不是一个普通的“跨系统授权”问题，也不是缺少某个统一签名协议。

更准确的问题是：

对一个 exact operation、exact object、exact version，系统如何分别取得并保持多个 Principal 所拥有的权威事实，使一次跨域行动在前进时不发生语义越权，并且事后能够回答：谁有权、谁授权了谁、允许做什么、谁保留反对权、什么被预约、谁作了承诺、何时撤销、谁接受了输出、争议由谁裁决？

本研究得到五个主要判断。

第一，不存在一个全局的 authorized=true。
Mandate、Authority、permission、relation stance、reservation、commitment、standing、challenge、revocation 和 acceptance 是不同 owner 控制的不同类型事实。它们只能通过任务特定的规则共同支持某个阶段的转换，不能互相替代。

第二，最强现成方案是组合，而不是单品。
成熟的身份与密钥栈、OAuth/RAR 或 GNAP、OPA/Cedar/OpenFGA/XACML、事务型 reservation ledger、CLM/e-sign、当前状态查询、人工审批与申诉已经能闭合大部分现实任务。没有证据表明现在应先发明一套新的通用权威协议。

第三，强中心在权威确实统一时应当获胜。
如果一个法律和运营 Principal 真正拥有全部资源、审批权和最终责任，那么中央 IAM、策略引擎、事务数据库、合同系统与人工复核通常具有最低延迟、最低维护成本和最清晰责任。反过来，如果供应商、患者、客户或外部组织仍保有不可代行的 Authority，中央 controller 只能协调，不能借“平台统一”代签。

第四，最危险的不是“没有签名”，而是“有效证据被错误升级”。
典型情况包括：

签名有效，但签名者没有对应 Mandate；

policy 确实返回 Allow，但输入已经过期；

reservation 成功，但预约的不是最终 object version；

aggregate signature 完整，但其中某个 Principal 的签名只表示 ACK；

workflow green，但 owner 从未 acceptance；

旧 stance 的签名仍可验证，但它已经被新 stance 撤销；

格式迁移成功，却丢失了 nonDelegable、purpose、objection 或 forbid。

第五，最稳定、最值得自研的 residual 不是另一个授权引擎。
更可能值得建设的是：

exact object/version 在异构系统间的绑定与差异检测；

ALLOW / REJECT / UNKNOWN / DEFER 的跨层保真；

多个独立 Authority 的 current-head、撤销和 TOCTOU 防护；

challenge/standing 在聚合、迁移和恢复中的保存；

跨格式迁移的语义差分测试和 loss manifest；

在无共同事务管理器时，对 reservation、commitment 和 execution 的 fenced coordination。

这些首先应实现为本地 IR、adapter contract、conformance suite 和运行时检查，而不是直接宣布为新网络协议。

二、重新定义研究对象
2.1 Exact Operation，而不是模糊的“任务”

一个待授权的联合行动应至少被表示为：

OperationCandidate Ω = {
  episode_id,
  stage,
  action,
  object_type,
  object_id,
  object_version,
  object_digest,
  principals,
  side_effects,
  amount_or_limits,
  dependencies,
  deadline,
  acceptance_rule
}

其中 stage 很重要。系统不是一次性判断“整个任务是否授权”，而是分别判断：

EligibleToRequest(Ω)
EligibleToDisclose(Ω)
EligibleToReserve(Ω)
EligibleToCommit(Ω)
EligibleToExecute(Ω)
EligibleToAccept(Ω)
EligibleToSettle(Ω)

一份 Mandate 可能允许 agent 发起询价，但不允许签合同；一份 policy Allow 可能允许创建 reservation，但不允许消耗资源；一个 ACK 可能表示收到结果，但不表示接受结果。

因此，所有决策都应写成：

Decision(stage, Ω)

而不是脱离阶段的 authorized=true。

2.2 每条权威事实都必须有 owner、来源和版本

统一证据结构可以表示为：

Evidence e = {
  evidence_type,
  owner,
  issuer,
  subject,
  predicate,
  operation_ref,
  scope,
  conditions,
  valid_from,
  valid_until,
  version,
  current_head,
  status,
  source_authority,
  proof,
  issued_at,
  observed_at
}

这里至少要区分：

owner：谁控制这一事实；

issuer：谁出具证据；

subject：证据描述谁；

source_authority：该事实的规范来源；

controller：负责协调流程的人或系统。

四者可能完全不同。Credential issuer 并不自动拥有被描述对象；controller 也不会因为收集了证据而获得其中的 Authority。

2.3 各对象的严格含义
对象	它本身证明什么	不自动证明什么
Identity / key	某请求或签名与某身份或密钥关联	该身份有权做此事
Authority	某 Principal 在特定规范域内有决定权、责任或否决权	当前愿意行动、已授权代理、资源可用
Mandate	grantor 在给定 scope 内委托 grantee 行动	grantor 自己确有该 Authority；当前 policy 允许
Permission	给定输入满足某 policy	输入真实、最新；Principal 已作承诺
Relation stance	Principal 当前支持、拒绝或附条件接受某关系	已预约资源、已签合同、已接受输出
Reservation	某资源或额度在一定时间内被持有	使用它在规范上合法；双方已承诺
Commitment	Principal 对 exact object/terms 作出可追责承诺	现实能力已准备；行动已经完成
Standing	某主体有权发起 challenge 或申诉	challenge 必然成立
Challenge	有人针对 exact object 提出反对或争议	必然停止行动；其效果取决于规则
Revocation	某份 Mandate、credential、stance 或 permission 的状态改变	所有历史签名都追溯失效
Acceptance	owner 接受某个 output 或履约结果	执行前的行为因此被追溯授权
ACK	收到消息、文件或通知	理解、授权、承诺或 acceptance
Workflow green	工作流内部步骤成功完成	外部 Authority、现实 Effect 或 acceptance 存在
Aggregate signature	一组密钥签过某个字节串	每个签名者均有适当 Authority；无人反对；所有人理解相同语义

最重要的系统不变量是：

没有明确、版本化的 typed rule，就不能把一种证据提升为另一种事实。

三、决策语义：必须保留 Unknown、Reject 和 Defer

本研究建议最低限度保留四种结果：

ALLOW

当前 stage 所要求的全部权威事实均为真、均指向同一个 exact object/version，并且在提交点完成了必要的强一致读回和 reservation/fence。

它只允许该 stage 转换，不表示后续 Effect、Acceptance 或 Settlement。

REJECT

存在一个足以否决该 stage 的权威负事实，例如：

owner 明确拒绝；

Mandate 已撤销；

controller 试图执行 non-delegable 动作；

object digest 不匹配；

challenge 根据规则具有 suspensive effect；

hard policy invariant 失败；

reservation 已被其他有效持有者占用且不允许等待。

UNKNOWN

缺少一个 material fact，或当前性、真实性、来源无法得到权威确认。例如：

无法访问当前 revocation head；

stance 只有缓存副本，无法确认是否已 supersede；

key status 不明；

迁移中发现一个无法解释的字段；

policy engine 收到了缺失属性。

UNKNOWN 是认识状态，不是 owner 的拒绝。默认拒绝执行是安全策略，但评测时不能把它算作“正确 Reject”。

DEFER

系统知道缺少什么、谁能解决、预计由何事件推进，但当前还不能安全转换。例如：

等待人工审批；

等待冷静期或申诉期；

等待另一个 reservation 释放；

等待 current-head 服务恢复；

等待 Principal 对修订版本重新签署。

若既存在足以否决的 authoritative negative，又存在其他 unknown，REJECT 可以成立，因为负事实已经充分。若没有充分负事实，只是证据不可得，则必须保留 UNKNOWN。

四、现成技术的实际覆盖
4.1 OPA

OPA 是通用策略引擎，适合把复杂上下文和异构事实编译成应用自定义的决策对象。其 decision logs 可以记录查询输入、被查询策略和 bundle metadata，适合作为策略层审计；但 OPA 官方也明确说明，OPA 通常持有的是外部数据和策略的缓存或副本，而不是它们的 source of truth。Bundle 分发本身是 eventual consistency。
Open Policy Agent
+3
Open Policy Agent
+3
Open Policy Agent
+3

最强角色：

跨多类输入的 policy aggregation；

自定义输出 ALLOW/REJECT/UNKNOWN/DEFER；

invariants、reason codes 和 migration guards；

策略决策审计。

原生缺口：

不拥有 Mandate、stance、reservation 或 commitment；

Rego 能表达“签名有效时允许”，但不能证明签名者有真实 Authority；

若把缓存数据当 current truth，会产生撤销延迟和 stale allow；

高灵活性也意味着语义大量由本地团队自行定义。

判断：
OPA 是本研究中最适合作为“组合决策编排层”的现成工具，但绝不能成为私有事实的免费 oracle。

4.2 Cedar

Cedar 把请求组织为 principal、action、resource 和 context，返回 Allow 或 Deny，并携带 determining policies 和错误诊断；显式 forbid 覆盖 permit，未获 permit 时默认 Deny。它支持 schema 验证，因而更容易发现 entity、action 和 attribute 的类型错误。
Cedar Policy Language Reference Guide
+3
Cedar Policy Language Reference Guide
+3
Cedar Policy Language Reference Guide
+3

最强角色：

typed application authorization；

边界清晰、可验证的权限策略；

wrong-resource、wrong-action 和 schema drift 的早期检测；

高速、嵌入式或服务端授权。

原生缺口：

最终决策是二值的，业务 Unknown 和 Defer 需要由外围系统保留；

policy error 虽有 diagnostics，最终仍可能呈现 Deny；

schema 迁移和 managed service 的状态传播必须另行治理；

不负责合同、reservation、owner challenge。

判断：
Cedar 在数字系统内部的 exact resource permission 上通常优于更松散的策略表达；但不能把它的 Deny 直接等同于 owner Reject。

4.3 OpenFGA

OpenFGA 原生回答的是“user 是否与 object 存在某种 relation”，结果本质上是 yes/no。它的 authorization models 不可变，每次更新产生新的 model version；API 可以显式指定 model ID，官方建议生产环境固定具体 model ID。它还提供查询一致性选项：启用缓存时，默认低延迟查询可能暂时看不到新 tuple，HIGHER_CONSISTENCY 会绕过缓存读数据库。
OpenFGA
+3
OpenFGA
+3
OpenFGA
+3

最强角色：

relation stance 的结构基础；

谁是 owner、member、delegate、reviewer、challenger；

standing 和组织关系；

可版本化的关系授权模型。

原生缺口：

relationship tuple 表示“系统记录了某关系”，并不证明 relation owner 以适当方式作出该 stance；

Check 是二值的，不能原生区分 Unknown、Reject 和 Defer；

关系成立不代表 reservation 或 commitment；

contextual tuple 如果来自未经验证的 token 或 controller 输入，可能把主张误当权威事实。

判断：
OpenFGA 是最强的关系和 standing 层候选，不是联合承诺系统。

4.4 XACML 与 ACAL/JACAL

XACML 3.0 原生区分 Permit、Deny、NotApplicable 和 Indeterminate，并支持 obligations、advice；另有 administration and delegation profile。就决策词汇而言，它比 Cedar/OpenFGA 更接近 G5 的多值需求。
OASIS Open
+2
OASIS Open
+2

但仍不能简单映射：

NotApplicable 不一定等于业务 Unknown；

Indeterminate 不一定等于 Defer；

obligation 不等于 commitment；

delegation policy 不证明 delegator 的外部法律 Authority。

XACML 3.0 是 2013 年的正式 OASIS Standard。它并非完全停更：OASIS XACML TC 在 2026 年 2 月发布了 ACAL 1.0 和 JSON 表示 JACAL 的 Committee Specification Draft 01，目标是形成技术无关、可 JSON 化的新一代模型；但目前是 draft，不应当当作成熟最终标准。
OASIS Open
+2
OASIS Open
+2

判断：
XACML 是标准化语义最丰富的 policy family，但实现和治理复杂度最高。对有成熟 XACML 团队的金融、政府或大型企业，它仍可能是最强选择；对新系统，不一定比 OPA/Cedar 加外围状态机更划算。

4.5 OAuth、RAR 与 GNAP

OAuth 负责把 delegated API access 交给软件。RAR 的 authorization_details 能携带细粒度 JSON 授权请求，例如金额、收款方、资源位置等；这比粗粒度 scope 更适合绑定 exact operation。GNAP 进一步把授权协商、客户端实例和授权结果作为核心对象。OAuth 安全最佳实践也在 RFC 9700 中持续更新。
RFC 编辑器
+2
RFC 编辑器
+2

它们能证明或传递：

client 被授权调用某 API；

请求的细粒度 action/object parameters；

token 与客户端密钥的绑定；

token 当前是否 active，取决于 introspection、TTL 和缓存策略。

它们不能证明：

resource owner 是否真的拥有某项企业、医疗或合同 Authority；

一次 API delegation 是否等于签订合同；

reservation 是否成功；

Principal 是否接受了最终输出；

controller 是否可以代替 Principal 作出 non-delegable 决定。

判断：
OAuth/RAR 是成熟组合中不可缺少的访问与授权传输层，但不是 Mandate 或 Commitment 的替代品。GNAP 更贴近动态软件代理授权，现阶段生态成熟度仍低于 OAuth。

4.6 VC 与 SD-JWT

W3C Verifiable Credentials Data Model 2.0 已于 2025 年成为 Recommendation，规定 issuer-holder-verifier 的可验证声明模型；Bitstring Status List 1.0 提供 suspension/revocation 状态机制。SD-JWT 已于 2025 年形成 RFC 9901，支持 JSON claim 的选择性披露和可选 holder key binding。
W3C
+2
W3C
+2

必须区分两个状态：

SD-JWT 本身：RFC 9901，已成为 Standards Track RFC；

SD-JWT VC profile：截至 2026 年 7 月仍是 draft-ietf-oauth-sd-jwt-vc-17，已进入标准流程但仍是 Internet-Draft。
IETF Datatracker
+1

最强角色：

可移植的资质、角色、license、delegation claim；

选择性披露，降低跨域披露成本；

holder possession；

issuer provenance 和 credential status。

原生缺口：

只证明 issuer 作出了某项 claim；

不能单独证明 claim 当前仍足以授权 exact operation；

status list、issuer trust、credential type、purpose 和 policy interpretation 仍由 verifier 负责；

Credential 的签发者、被描述主体和真正 Authority owner 可能不同。

判断：
VC/SD-JWT 是证据携带层，不是联合行动的最终裁决层。

4.7 CLM 与 e-sign

现代 CLM 管理合同创建、协商、路由、批准、签署、存储和后续生命周期；DocuSign CLM API 也支持文档下载和版本管理。
DocuSign
+1

e-sign 的主要价值是：

exact document/version；

签署事件与时间；

签署人身份验证方式；

audit trail；

decline、recall、cancel 等事件。

但 e-sign 不是自动的 Authority 证明。Adobe 对 API/embedded signing 的官方说明明确指出：签署平台的 audit trail 必须和集成应用自己的认证、访问日志一起解释，任何一方的记录单独使用都不能完整说明“谁通过什么应用身份完成签署”。
Adobe 帮助中心
+1

这正是 controller 代签风险的现实入口：

controller 能创建 envelope；

controller 或集成应用可能控制 signing session；

e-sign 平台证明了签署动作，却未必证明外部应用没有错误地把 session 交给其他人；

即使人确实签了，也还要独立验证其企业 Mandate 和非代行限制。

判断：
CLM/e-sign 是成熟组合中最强的 Commitment 层，却不是 live permission、reservation 或 output acceptance 层。

4.8 Reservation DB

Reservation 的核心不是签名，而是并发安全。

PostgreSQL 的 range exclusion constraint 可以原子阻止时间区间重叠；Serializable isolation 能发现无法与串行执行等价的并发；SELECT ... FOR UPDATE 可以锁住当前资源记录；幂等键则防止网络重试制造重复操作。
Stripe 文档
+3
PostgreSQL
+3
PostgreSQL
+3

最强角色：

唯一 reservation；

capacity/time window 冲突；

lease、expiry 和 fencing token；

幂等重试；

commit-time CAS 和版本检查。

原生缺口：

数据库只知道约束，不知道谁在规范上有权预约；

reservation 不等于供应商承诺交付；

reservation 成功也不等于 object version 未变化。

判断：
对于稀缺资源，数据库约束通常比任何“权威协议”更可靠。先用事务把重复 reservation 解决掉，再讨论高层语义。

4.9 人工审批、申诉和挑战

人工制度不是不得已的失败兜底。对于真实 norm、standing、例外、利益冲突和争议，它往往是唯一真正拥有 Authority 的层。

NIST 的治理材料明确要求区分人类与 AI 的职责，设置反馈、recourse、appeal、override，并记录投诉、响应时间、override 和 adjudication 活动。
NIST出版社
+2
NIST AI Resource Center
+2

其有效前提是审批界面必须展示：

exact object/version/digest；

与上一个版本的差异；

审批人正在执行的 Authority role；

Mandate 范围；

拒绝和附条件批准；

challenge 的效果和去向。

只给人一个“Approve”按钮，而不显示对象差异和权威来源，不是 human-in-the-loop，而是 human rubber stamp。

4.10 强中心与通用模型
强中心

当一个实体真正拥有全部 Authority 时，强中心可以在一个 ACID transaction 中完成：

policy evaluation；

Mandate lookup；

reservation；

commitment record；

execution fence；

audit。

这应是内部 IT、统一企业资源调度和单一运营方场景的首选基线。

强中心失效的边界不是技术，而是权威拓扑：

外部 Principal 保留不可代行 Authority 时，中央平台不能通过“更完整的数据库”获得该 Authority。

通用模型

通用模型适合：

从合同和政策中提取候选字段；

生成差异摘要；

辅助映射 Rego、Cedar、XACML、FGA 和 CLM schema；

识别可能丢失的 migration fields；

生成人工审批解释和测试案例。

通用模型不应：

成为 Mandate source；

用 controller 的 key 替 Principal 签名；

根据语言上的“看起来同意”生成 stance；

把缺失证据补全成 Allow；

决定自己是否拥有 Authority。

它是编译器、解释器和异常探测器，不是权威主体。

五、停更、格式、许可、锁定和自持审计

以下为截至 2026 年 7 月 29 日的状态判断。

技术	当前状态	主要格式	许可与自持	锁定风险
OPA	活跃，CNCF Graduated	Rego、JSON、bundle、REST	Apache-2.0，可完整自持	低—中；主要是 Rego 和本地数据约定
Cedar	活跃	Cedar policy、Cedar/JSON schema、JSON entities	Apache-2.0，可嵌入和自持；AWS 托管版本另算	开源核心低—中，托管控制面中
OpenFGA	活跃	FGA DSL、JSON model、relationship tuples、HTTP/gRPC	Apache-2.0，可自持并使用 PostgreSQL/MySQL/SQLite	中；模型与 tuple 语义迁移有成本
XACML	3.0 核心稳定；ACAL/JACAL 2026 draft	传统 XML；新草案含 JSON 表示	标准公开，具体引擎许可证不同，可选择自持实现	中—高；复杂 profile、vendor extension 和工具链
OAuth/RAR	成熟活跃	HTTP、JSON、JWT/JWS	开放 RFC；实现许可证不同，可自持 AS/RS	协议层低；claim/profile 和 IAM 运维中
GNAP	已有 RFC，生态较新	HTTP、JSON、签名与 key-bound artifacts	开放 RFC，可自持，但实现选择较少	当前中，主要来自生态成熟度
W3C VC 2.0	Recommendation	JSON-LD、Data Integrity 或 enveloped proof	标准公开；实现可自持	中；DID、status、cryptosuite、profile 组合
SD-JWT	RFC 9901 已完成；SD-JWT VC profile 仍为 draft	JWS、Disclosure、KB-JWT	标准公开；实现可自持	基础格式低—中，credential profile 中
CLM/e-sign	活跃商业产品	PDF/DOCX、vendor JSON、audit report	本研究比较的主流产品主要为商业云平台	高；签署 PDF 可导出，但工作流、metadata、模板和审批历史迁移困难
PostgreSQL reservation	活跃成熟	SQL、range、constraint、transaction	PostgreSQL License，可完整自持	低—中；主要是应用 schema 和存储过程

OPA、Cedar 和 OpenFGA 均为 Apache-2.0 开源实现；OpenFGA 官方文档还明确支持自部署以及多种后端数据库。
OpenFGA
+3
GitHub
+3
GitHub
+3
 PostgreSQL 使用宽松的 PostgreSQL License。
PostgreSQL

这里有三个容易误判的地方：

XACML 不是“已经死亡”，但 XACML 3.0 的成熟性和 ACAL/JACAL 的新鲜性必须分开评价。

SD-JWT 已是 RFC，不等于 SD-JWT VC profile 已完成。

可导出 signed PDF，不等于可无损导出 CLM 的完整规范语义。 批注、审批角色、条件批准、委托链、撤回原因和 workflow state 常常属于另一套 vendor model。

六、最强“无需新协议”端到端基线

下面称为 MCB-G5，只是 benchmark 中的“成熟组合基线”名称，不是新协议。

6.1 组件构成
A. 身份与密钥历史

使用成熟 IdP、PKI、OIDC/OAuth，并保存：

key ID；

valid_from / valid_to；

rotation；

compromise time；

revocation reason；

historical verification rule；

Principal 本人或其合法 signing service 对 private key 的控制。

Controller 只能请求签署，不能持有 non-delegable Principal key。

B. Authoritative registry

对每个 Mandate、stance、standing 和 revocation 保存：

owner
source_authority
scope
object_selector
actions
limits
delegable / nonDelegable
conditions
version
supersedes
current_head
validity interval
revocation semantics

它可以使用普通关系数据库、VC、企业目录或 CLM 实现。关键不在格式，而在它是不是相应 owner 的 authoritative readback。

C. Exact-operation envelope

所有层共享同一个 operation reference：

operation_id
object_id
object_version
object_digest
action
principal roles
critical parameters
side effects
acceptance rule

RAR、policy request、reservation row、e-sign document 和 execution command 都必须引用它。只使用名称、标题、ticket number 或自然语言描述不够。

D. 策略与关系层

按任务选择：

OPA：异构复杂规则和四值结果；

Cedar：typed application permission；

OpenFGA：owner、delegate、member、challenger、standing；

XACML：已有企业 policy administration 和 obligations 生态时使用。

不要求四者全部部署。

E. Reservation ledger

使用：

unique/exclusion constraint；

serializable transaction 或适当行锁；

lease expiry；

fencing token；

idempotency key；

exact object/version；

owner 和 purpose。

Reservation 不能只存在于 workflow variable 或消息队列中。

F. Commitment 层

使用 CLM/e-sign 或领域原生合同系统，对以下内容签署：

exact operation digest；

terms/version；

signer role；

Mandate reference；

conditions；

expiry；

amendment 和 termination 规则。

Aggregate signature 只是聚合证明；每个 participant 的 role、scope 和 individual evidence 必须可恢复。

G. Challenge 和 appeal

Challenge 至少是：

challenge_id
challenger
standing_ref
operation_ref
grounds
evidence
filed_at
effect = suspensive | non_suspensive | compensatory
adjudicator
deadline
outcome
appeal_ref

“收到投诉工单”不等于 challenge coverage。系统必须知道 challenge 是否暂停 execution、只暂停 settlement，还是只产生后续补偿权。

H. Acceptance

Acceptance 必须独立于 execution receipt：

accepting_owner
accepted_object/output version
acceptance criteria version
accepted / rejected / conditional / disputed
reason
timestamp
proof

不能用“没有投诉”“下载了文件”或“ACK 200”自动替代。

6.2 Commit-time read set

每次高风险提交应形成一个 read set：

R = {
  object_head,
  policy_version,
  authorization_model_id,
  mandate_head[principal],
  stance_head[principal],
  standing_and_challenge_head,
  credential_status_head,
  signer_key_status,
  reservation_version,
  commitment_version
}

提交步骤为：

读取所有 required facts；

分类为 Allow、Reject、Unknown 或 Defer；

原子取得 reservation 和 fence；

再读容易变化的 current heads；

验证 read set 未改变；

对 exact digest 获取必要签名；

执行时携带 fencing token；

保存 evidence package；

后续单独取得 output acceptance。

该 evidence package 只能证明“controller 当时检查了哪些证据”，不能把 controller 提升为这些证据的 owner。

6.3 强中心分支

在真正单一 Authority 的任务中，可以把上述 registry、policy、reservation 和 commitment record 合并到同一个中央事务系统，从而减少：

网络往返；

stale window；

adapter；

多格式迁移；

人工复核。

这不是较低级的方案，而很可能是正确答案。

只有在外部 Principal 的 Authority 不可被中央实体合法吸收时，才需要跨域 current-head、独立签署和 challenge preservation。

七、三个真实任务及公平基线
7.1 任务 A：跨企业制造采购与产能锁定
Principals

买方业务 owner；

预算 owner；

采购/法务；

供应商销售授权人；

供应商工厂排产 owner；

质量验收 owner。

Exact object
BOM revision
drawing/spec digest
SKU and quantity
tolerance and material
price and currency
Incoterm
delivery window
inspection rule
change-control rule
必需事实

买方 agent 的询价/下单 Mandate；

预算与供应商准入 policy；

供应商当前商业 stance；

工厂产能 reservation；

双方对 exact PO/version 的 commitment；

质量或合规 challenge；

到货检验 acceptance。

注入故障

BOM v7 获批后执行 v8；

供应商旧报价 stance 重放；

买方签署 Mandate 在下单前撤销；

两个订单竞争同一产线窗口；

供应商签名 key 轮换；

CLM 迁移丢失“未经书面同意不得替代材料”。

最适合的成熟组合

OAuth/RAR + OPA/OpenFGA + PostgreSQL reservation + CLM/e-sign + 人工争议与验收。

强中心只有在买卖双方属于同一实际控制且 Mandate 可合法集中时才是有效对照。

7.2 任务 B：跨机构医疗转诊、手术排期与数据披露

这是实验任务设计，不构成医疗或法律建议。

Principals

患者；

转诊医生；

执行医生和医院；

保险或付款方；

手术室/设备 owner；

隐私和合规 owner。

Exact object
patient identity
procedure/order version
clinical indication
performing clinician
facility
scheduled time
data disclosure scope
consent document version
payer authorization reference
必需事实

医生的执业和机构 privilege；

患者 consent 和数据披露 stance；

payer prior authorization；

机构 policy；

手术室、设备和人员 reservation；

患者 withdrawal、临床 objection 和保险 appeal；

术后记录、报告、claim 等不同 owner 的 acceptance。

这个任务特别能证明：不存在单一的“最终 acceptance”。患者、医院、转诊方和付款方可能分别接受或拒绝不同对象。

注入故障

患者在预约后撤回 consent；

payer authorization 指向旧 procedure code；

医生 credential 有效但当前 privilege 已暂停；

手术室 reservation 成功但执行医生更换；

数据披露同意书迁移后丢失 purpose limitation；

challenge 已提交但 workflow 仍显示 green。

最适合的成熟组合

VC/status 用于资质证据；OAuth/RAR 用于数据访问委托；XACML 或 OPA 用于政策；数据库用于排期；e-consent/e-sign 用于承诺；人工负责临床例外、withdrawal 和 appeal。

强中心不能合法吞并患者 consent、医生专业判断和 payer appeal。

7.3 任务 C：多租户生产环境发布
Principals

application owner；

developer/team lead；

security owner；

platform/SRE；

customer tenant owner；

change manager。

Exact object
artifact digest
source revision
configuration version
target environment
tenant scope
database migration version
maintenance window
rollback artifact
expected SLO and acceptance test
必需事实

developer 的 deployment Mandate；

security 和 platform policy；

tenant relation/stance；

maintenance window reservation；

signed change record；

emergency/break-glass rule；

customer challenge；

post-deploy acceptance 与 rollback authority。

注入故障

审批后重新构建 artifact；

policy Allow 后权限立即撤销；

两个 deployment 争夺同一数据库迁移窗口；

旧 tenant stance 重放；

key rotation 后仍接受旧 live token；

从原 change system 迁移时丢失“仅 staging”字段。

最适合的成熟组合

OIDC/OAuth + Cedar/OPA/OpenFGA + transactional deployment lock + signed artifact/change record + SRE 人工 gate。

当所有团队和 tenant 均由同一运营实体合法控制时，强中心预计会在安全、延迟和维护成本上获胜。这一结果应被视为正向结果，而不是研究失败。

八、公平实验设计
8.1 两级比较，避免类别错误
第一级：组件原生覆盖测试

每个产品只测试其声称负责的事实：

policy engine：policy decision；

OpenFGA：relationship/standing；

OAuth：delegated API access；

VC：claim authenticity/status；

e-sign：签署证据；

DB：reservation uniqueness；

human process：challenge 和 exception。

不因 e-sign 不能做排期而判它“失败”，也不因 PostgreSQL 不能证明企业 Mandate 而判数据库“失败”。

第二级：端到端组合测试

至少比较：

Policy-only controller：单个策略引擎加薄 enforcement；

MCB-G5：最强成熟组合；

Valid strong center：权威真实统一的中央实现；

General-model orchestrator：模型使用相同外部工具，但无额外 oracle；

Ablations：逐项去掉 exact binding、current-head、transactional reservation、challenge 或 human gate。

8.2 公平条件

所有方案必须获得相同的：

authoritative source APIs；

网络延迟与故障分布；

clock；

key 和 credential；

object schema；

human reviewer pool；

policy 与业务规则；

disclosure budget；

缓存与一致性预算。

禁止：

给某方案隐藏的 ground-truth API；

让 controller 直接读取 Principal 私有世界；

用 simulator label 当现实 dependency；

给强中心不存在的外部 Authority；

把 Unknown 自动标成 Reject 后宣称准确率高。

8.3 Ground truth

Truth oracle 只供评测，不供被测系统调用。它记录：

authoritative event time
effective time
owner
object/version
mandate state
stance state
policy state
reservation state
commitment state
challenge state
key state
acceptance state

评分依据是 commit instant 的真值，不是最终日志看起来是否一致。

九、指标定义
9.1 False Allow

同时报告两个分母：

Unsafe-allow precision risk
= unsafe ALLOW / all ALLOW

Unsafe escape rate
= unsafe ALLOW / all oracle-non-ALLOW cases

应按伤害严重度加权。Controller 代签、wrong-patient、wrong-artifact 等不能与普通缺字段同权。

对于安全关键案例，如果观察到零次 false allow，也要报告统计上界。零事件时，95% 上界可近似用 3/n；例如 30,000 个独立高风险案例中零事件，只能支持 false-allow rate 大约低于 10^-4，而不是证明绝对为零。

9.2 False Deny
false hard reject
= system REJECT while oracle ALLOW

UNKNOWN 和 DEFER 不计入 false deny，而应分别评分，否则系统只要全部拒绝就会获得虚假的安全优势。

9.3 Unknown / Reject / Defer precision 与 recall

逐类报告：

correct Unknown；

Unknown 被错误升级为 Allow；

authoritative Reject 被错标为 Unknown；

可解决的 Defer 被永久卡成 Unknown；

不可恢复的 Reject 被错误当作 Defer 无限等待。

推荐使用 per-class precision、recall 和 confusion matrix，不只报告总体 accuracy。

9.4 撤销延迟
revocation latency
= last unsafe allow time
  - authoritative revocation effective time

分解为：

source publication latency；

propagation latency；

cache latency；

decision refresh latency；

enforcement latency。

报告 p50、p95、p99 和最大值，并区分：

prospective revocation；

temporary suspension；

supersede；

key compromise；

retroactive invalidation。

9.5 重复 reservation
duplicate reservation rate
= conflicting committed reservations
  / contention episodes

另报：

重复网络请求产生的副作用；

lease expiry 后旧 actor 是否还能执行；

fencing token 拒绝旧 executor 的比例；

crash recovery 后 reservation 泄漏时间。

9.6 Challenge coverage

一个 challenge ground 只有同时满足以下条件才算完整覆盖：

能识别有 standing 的主体；

有可用 intake；

绑定 exact object/version；

记录 challenge 的 suspensive 或其他 effect；

有责任 adjudicator 和时限；

有理由、结果、appeal 和不可抵赖审计。

按业务严重度加权，分别报告六项，避免用单一“有投诉入口”冒充完整覆盖。

9.7 跨格式迁移语义损失

至少报告四个独立维度：

Field loss
Constraint loss
Behavioral divergence
Provenance/negative-fact loss

方法是对迁移前后运行同一组 differential cases，检查：

Allow/Deny/Unknown/Defer 是否一致；

exact object/version 是否一致；

forbid/negative stance 是否保存；

conditions、purpose、nonDelegable 是否保存；

issuer、owner、source authority 是否仍可追溯；

round trip 后是否可恢复。

任何无法解释的字段必须进入 loss manifest，并默认阻止自动 Allow。

9.8 人工、披露和维护成本

人工成本：

每 episode 人工分钟数；

handoff 次数；

p95 队列时间；

reopen 比例；

reviewer disagreement；

challenge adjudication 时间。

披露成本：

每个 Principal 暴露的字段；

数据敏感等级；

是否只披露最小必要 claim；

通过选择性披露节省的内容；

为确认 Authority 是否被迫披露内部组织结构。

维护成本：

每月 policy/schema/adapter 工时；

升级和迁移工时；

incident 和 on-call；

restore/export drill；

trust root 数量；

vendor-specific fields；

格式往返失败率。

十、六类强制反例
10.1 Controller 代签
构造

Principal P 有不可转委托的签约 Authority；

controller C 有权创建 e-sign envelope 和取得 embedded signing URL；

C 的系统认证有效；

最终 PDF 和 audit trail 均完整；

P 从未亲自控制 signing session。

错误结论

“签名平台显示 P 已签，因此 P 已承诺。”

正确结果

REJECT。若无法确定 session 由谁控制，则为 UNKNOWN，不能 Allow。

防线

Principal-controlled key 或受监管 remote signing；

app authentication log 与 e-sign audit 联合验证；

独立 Mandate 检查；

nonDelegable flag；

controller 只能 transport，不得成为 signer。

Adobe 对 embedded signing 的说明正好证明了为什么签署平台日志本身不足以还原应用侧身份链。
Adobe 帮助中心

10.2 旧 stance 重放
构造

stance v17 = SUPPORT，签名仍有效；

owner 随后发布 v18 = OBJECT 或 REVOKED；

controller 只持有 v17；

v18 current-head 服务暂时不可用。

正确结果

确认 v18 时：REJECT；

无法确认 current head 时：UNKNOWN；

绝不能因为 v17 签名有效而 Allow。

防线

monotonic owner head；

supersedes；

expiry；

authoritative readback；

replay cache；

evidence 中记录 observed head。

10.3 TOCTOU
构造
t0: policy Allow
t1: Mandate revoked or object updated
t2: reservation acquired
t3: execution begins
错误结论

“t0 已经批准，因此 t3 可以执行。”

正确结果

在 commit/execute fence 处重新读取关键 head。若变化，进入 REJECT、UNKNOWN 或重新 DEFER。

防线

commit-time read set；

optimistic version check；

short lease；

fencing token；

current-head strong read；

object digest 重新校验。

10.4 Wrong object / wrong version
构造

人工审批界面显示“部署支付服务”；

审批的 digest 是 A；

重建或配置变化后实际 artifact 是 B；

ticket ID 和名称均未变化。

正确结果

REJECT。标题相同不构成对象相同。

防线

所有 approval、reservation、commitment 和 execution 绑定 digest；

UI 显示差异；

参数规范化和 canonicalization；

禁止未解释的 post-approval mutation。

10.5 Key rotation

必须区分三种情况：

旧 key 在有效期内签署历史合同，之后正常轮换。
历史 commitment 不应仅因轮换自动失效。

旧 key 在轮换之后签署 live authorization。
应 Reject。

发现旧 key 早已 compromise。
是否追溯无效取决于 compromise time、timestamp、领域规则和 adjudication，可能进入 Challenge/Defer。

因此，key inactive now 不能简单映射为“所有历史签名无效”，而 signature cryptographically valid 也不能映射为“当前 live permission 有效”。

10.6 Migration field-drop
构造

从 CLM、VC、XACML、OpenFGA 或本地 registry 迁移到统一 JSON，以下字段之一被丢弃：

nonDelegable
purpose
objectDigest
validUntil
supersedes
negative stance
forbid
objection
standing
credentialStatus
policyVersion
conditional acceptance

目标系统仍能成功解析，并返回 Allow。

正确结果

迁移系统必须：

显式报告 field loss；

对测试语料运行 behavioral differential；

对未知 mandatory field fail closed；

保存 source provenance；

禁止把“解析成功”当“语义等价”。

这一类反例预计会是跨产品迁移中最稳定的 residual。

十一、预注册的方向性假设

以下是需要被实验推翻的假设。

H1：单一 policy engine 无法端到端闭合 G5

即使 OPA 或 XACML 能编码所有条件，只要 Mandate、stance、reservation 和 commitment 仍来自无权威保证的输入，策略引擎只是在精确计算错误或过期的数据。

H2：OPA 在自定义四值决策上占优，XACML 在标准多值语义上占优

Cedar 和 OpenFGA 预计需要外围 wrapper 才能保留 Unknown/Defer，但可能在 typed application authorization 和 relation checks 上获得更低维护成本。

H3：事务型 reservation 会显著降低重复副作用

无 exclusion/unique constraint、idempotency 和 fence 的 workflow，即使步骤全部 green，也预计会在 crash/retry 和并发下产生重复预约。

H4：强中心将在任务 C 的统一 Authority 版本中获胜

预计表现为：

更低撤销延迟；

更少 adapter；

更低人工成本；

更少 Unknown；

更低迁移损失。

若权威确实统一，这不是反例，而是正确架构选择。

H5：强中心在任务 A/B 的独立 Principal 版本中不能合法获得同样 recall

它要么：

等待外部 owner readback；

返回 Unknown/Defer；

或通过 controller substitution 制造 false allow。

H6：通用模型可以降低转换和人工阅读成本，但不能安全提高 Authority recall

除非模型被赋予新的 authoritative interface，否则它只能更好地理解已有证据，不能创造缺失的授权事实。

H7：最难清除的 false allow 将来自跨层绑定，而非单层策略错误

预计主要集中于：

wrong-object；

stale head；

key/mandate 时序；

aggregate evidence 升级；

migration field-drop；

controller proxy-sign。

十二、成熟组合已经闭合了什么

在正确配置和真实 Authority source 存在时，现成技术已经分别闭合：

问题	成熟闭合手段
谁发起请求	IdP、OIDC、PKI、key binding
软件可调用什么 API	OAuth、RAR、GNAP
给定输入是否满足权限规则	OPA、Cedar、XACML
谁与什么对象存在何种关系	OpenFGA
某 issuer 是否作出某项 claim	VC、SD-JWT
Credential 是否暂停或撤销	status list、introspection、authoritative registry
稀缺资源是否唯一持有	ACID DB、exclusion constraint、lease、fence
谁签署了哪个文档版本	CLM、e-sign、audit trail
谁可提出异议、谁裁决	人工制度、case management、appeal
输出是否被 owner 接受	domain acceptance workflow
所有检查和引用是否可追溯	append-only audit/evidence package

因此，G5 目前没有证明需要重新发明：

身份系统；

通用 policy engine；

通用 credential；

通用电子签名；

通用 reservation service；

通用 workflow；

通用事件总线。

十三、仍然存在的 residual
13.1 工程 residual

这些通常可以用应用层 schema、adapter 和事务模式解决：

exact object digest 在 OAuth、policy、DB 和 CLM 间传递；

current-head API；

reason codes；
-四值结果 wrapper；

reservation fence；

key history；

challenge case object；

acceptance record；

migration loss manifest。

在完成这些之前，不应把问题归因为“缺少协议”。

13.2 稳定研究 residual

只有以下问题在最强成熟组合之后仍持续出现，才可能值得新研究。

A. 无共同事务管理器的跨 Authority commit

多个 Principal 可在不同时间撤销，且没有一个共同数据库。如何在不冻结所有人的情况下保证：

所有人签的是同一 object/version；

reservation 未过期；

current heads 未变化；

无 controller substitution；

failure 后不会半承诺、重复执行。

成熟的 lease、prepare/confirm、saga 和 compensation 能部分解决，但不能把独立 Principal 的可撤销意志变成真正 ACID transaction。

B. 跨格式的可证明语义保存

OPA、Cedar、XACML、OpenFGA、VC 和 CLM 不是同一种逻辑。一个转换器说“转换成功”，不能证明：

deny precedence 一致；

conditions 一致；

absence semantics 一致；

negative facts 保存；

provenance 保存；

object identity 一致。

需要的是 differential conformance，而不是另一个万能 schema。

C. Challenge 和 minority objection 的聚合保存

Aggregate signature 或联合 receipt 容易掩盖：

谁只是 ACK；

谁附条件支持；

谁提出 objection；

objection 是否 suspensive；

谁有 standing；

谁可撤销。

这是普通 multisig 无法自行解决的规范语义。

D. Freshness 与隐私的张力

Verifier 需要确认 Mandate、stance 或 credential 当前有效，但 owner 不愿暴露完整内部状态。如何只证明“对该 exact operation 当前仍有效”，同时减少通过多次查询重建 owner 内部 policy，是可能稳定存在的研究问题。

十四、什么时候才值得自研

一个 residual 至少同时满足以下条件，才应进入专用机制或协议研究：

在三个任务中至少两个重复出现；

在最强成熟组合下仍造成可测 false allow、false deny 或超标撤销延迟；

不是因为错误配置、缺少事务约束或没有调用现成 current-status API；

在至少两种独立产品或格式迁移中复现；

通过增加人工流程也不能以更低全生命周期成本解决；

有明确 counterfactual：移除新机制后指标显著恶化；

新机制不要求 controller 获得原本不存在的私有真值或 Authority；

能给出 conformance test，而不只是一套本体名词。

最合理的自研顺序是：

第一阶段：内部 IR

先建立一个本地 canonical representation：

OperationRef
AuthorityEvidenceRef
MandateRef
DecisionState
CurrentHeadRef
ReservationFence
CommitmentRef
ChallengeRef
AcceptanceRef
MigrationLoss

它只是 adapter 之间的内部合同。

第二阶段：conformance suite

发布：

六类反例；

三任务数据生成器；

differential migration corpus；

revocation race harness；

controller-substitution tests；

指标计算器。

第三阶段：只标准化稳定交集

若多个独立组织确实需要交换同样的最小对象，再考虑把其中一部分形成 profile。此时仍应优先复用 JSON、OAuth/RAR、VC、e-sign 和普通 API，而不是从 transport 开始另造系统。

最终裁决

G5 当前不支持“必须发明一套新的权威协议”这一结论。

最强的无新协议答案是：

用成熟身份和 delegated-access 栈确认调用者；用 OPA/Cedar/XACML 和 OpenFGA 分别处理 policy 与关系；用 owner-controlled registry 保持 Mandate、stance、standing 和 revocation current heads；用事务数据库处理 reservation；用 CLM/e-sign 处理 exact commitment；用人工制度处理 challenge、例外与申诉；最后用 exact object digest、commit-time read set、fencing token 和独立 acceptance 将这些层连接起来。

强中心在真实单一 Authority 下应当成为首选，甚至应当在任务 C 等场景赢得基线。

跨域情况下，controller 的正确身份不是“全局授权者”，而是：

不能代签、不能补全私有真值、不能把 Unknown 升为 Allow，只负责收集 owner-controlled evidence、检查 exact binding、协调有界等待、执行 fenced transition 并保存可追责证据的 coordinator。

若后续实验仍发现稳定 residual，最值得首先建设的不是新 authorization language，而是跨层语义保真、current-head/freshness、challenge preservation 和 migration differential testing。这比再增加一种签名、receipt 或 allow engine 更接近 G5 的真正未闭合部分。

