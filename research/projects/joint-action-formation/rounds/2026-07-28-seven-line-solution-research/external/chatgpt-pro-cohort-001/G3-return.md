# G3 ChatGPT Pro return

- Conversation: https://chatgpt.com/c/6a69e303-7cb4-83ea-b3ba-47b1a969dd66
- Captured: 2026-07-29
- Status: external candidate evidence; not independently validated
- Preservation note: assistant visible text transcribed verbatim from the signed-in in-app browser; page structure and link previews are not embedded here.

---

G3 独立重建：从“创造可能性”改写为“同一 Episode 下的合格路径形成”
一、核心结论

这条母线是成立的，但原问题里有一个必须先修正的逻辑歧义：

如果培训、采购、授权、建立伙伴关系、配置恢复机制本身也被算作“路径中的动作”，那么只要系统能先做这些动作，再执行任务，形成动作 + 执行路径 从 S0 起就已经是一条路径。

因此，“S0 中不存在路径，系统后来通过行动创造了一条路径”在单层路径定义下是自相矛盾的。

更准确的对象应分为两层：

当前合格执行路径：在当前能力、资源、关系、权限和恢复条件下，能够直接承担目标任务的路径。

条件形成轨迹：合法改变上述条件，使第一层路径集合从空集变为非空的干预序列。

于是 G3 真正研究的是：

在保持同一 coordination Intent、Q、V0、必要 Principal 和 Authority 拓扑不变的前提下，系统能否找到并实施一组合法、可验证、成本可接受的条件干预，使此前不存在的“当前合格执行路径”首次出现，并证明这不是发现、恢复、降标、替代主体或新建了另一个任务 Episode。

这不是一种必然需要新协议的计算问题。我的初步结论是：

在封闭、动作模型已知、Authority 可集中、政策可查询的环境里，它基本已经被规划器、约束求解、IAM、工作流、人类审批和恢复机制的组合解决。

在开放世界、多独立 Authority、私有意愿与动态政策中，剩余难点主要不是“再发明一个 planner”，而是：

如何证明 S0 中确实没有合格路径；

如何证明 Q、V0、Principal、Authority 没有漂移；

如何证明新增条件在真实世界中生效；

如何证明这些条件对新路径具有因果贡献；

如何在不可免费查询的私有事实下正确地询问、等待、被拒绝或返回 UNKNOWN。

当前没有足够依据说明这些 residual 必须由一套全新协议解决。更合理的第一产物是严格基准、Episode 完整性判定器和形成证据判定器。

二、形式对象重建
2.1 Episode 不是一句自然语言目标

定义一个固定 Episode：

E=⟨I,Q,V
0
	​

,P
\*
,A
\*
,B,H,ν⟩

其中：

I：已经形成并可表达、可由主体确认的 coordination Intent。本母线不处理 vague seed → Intent。

Q：合格判据，不只是终态目标，而应拆为：

Q=Q
effect
	​

∧Q
process
	​

∧Q
evidence
	​

∧Q
acceptance
	​

∧Q
time
	​


effect：现实中必须发生什么；

process：哪些过程约束不得违反；

evidence：必须产生什么证明；

acceptance：谁有权确认交付可接受；

time：时限、有效期、顺序要求。

V
0
	​

：各受保护 Principal 的最低价值条件。它不应被压成一个平均效用分数，而应是带 veto 的向量或偏序。

P
\*
：必要 Principal 集合，包含哪些身份固定、哪些角色允许从合格集合中替换。

A
\*
：所需 Authority 关系，包括谁能：

改变条件；

授权执行；

绑定某个 Principal；

接受最终 Effect；

委托或撤销权限。

B：声明的世界闭包边界，例如允许搜索哪些市场、哪些组织、哪些动作类型。

H：规划与有效性的时间范围。

ν：Episode 版本及修订历史。

这里最重要的是：Q、V0、Principal 和 Authority 必须是一等对象，而不是藏在 prompt 里的软描述。

2.2 必须区分真实世界和系统模型

定义：

W
t
	​

：时刻 t 的真实世界；

M
t
	​

：系统关于世界的模型；

O
t
	​

：系统获得的观察、文档、API 返回和声明；

Ω
t
	​

：当前真实政策和 Authority 状态。

系统可能在 M
t
	​

 中找不到路径，但 W
t
	​

 中实际存在路径；也可能在模型中找到路径，但真实政策或主体意愿并不允许。

因此，“没有路径”至少有三个不同状态：

CERTIFIED_EMPTY(B,H,t)：在明确闭包 B、时间范围 H 和足够完整的 authoritative state 下，可证明没有路径；

EVIDENCE_EMPTY：已查询了合理范围但无法证明完整；

UNKNOWN：缺少关键事实，尤其是私有意愿、实时产能、动态政策或不可代行审批。

在开放世界里，不允许把“planner 没找到”写成“现实中不存在”。

2.3 四类动作

把动作分为四类，可以避免大量伪形成：

1. 任务执行动作 A
T
	​


直接推进原任务 Effect，例如：

运行受控数据分析；

加工零件；

部署补丁。

2. 条件形成动作 A
F
	​


改变任务路径的现实可行条件，例如：

真正获得新技能；

购买工具；

获得当前有效权限；

签订并形成伙伴承诺；

建设、测试恢复机制；

获得认证或有约束力的批准。

3. 认知与发现动作 A
K
	​


只改变系统知识，而不改变实际世界，例如：

搜索数据库；

重新读文档；

修正错误模型；

发现一条本来就存在的路径；

将自然语言翻译成 PDDL；

找到一家原本已经合格、可签约且有产能的供应商。

4. Episode 修改动作 A
E
	​


改变 Q、V0、必要 Principal、Authority 或核心 Intent，例如：

放宽质量标准；

延长期限；

改换数据集或研究问题；

取消某个必须审批的主体；

接受更高风险或更低价值。

这些动作可能完全合法，但产生的是：

E→E
′

它们属于 AUTHORIZED_NEW_EPISODE，不能计入原 Episode 的 G3 成功。

2.4 “合格路径”的定义

令：

Π
E
	​

(W
t
	​

)=
⎩
⎨
⎧
	​

π∈A
T
\*
	​

∣
π 在真实世界可执行
Q
E
	​

(π,W
t
	​

)=1
V(π)⪰V
0
	​

P
\*
 得到满足
A
\*
 当前有效且未被冒用
	​

⎭
⎬
⎫
	​


G3 的起点是：

Π
E
	​

(W
t
0
	​

	​

)=∅

系统实施一条条件形成轨迹：

δ=⟨f
1
	​

,…,f
k
	​

⟩,f
i
	​

∈A
F
	​


使世界变为 W
t
1
	​

	​

，并且：

Π
E
	​

(W
t
1
	​

	​

)

=∅

但这还不足以构成成功。完整成功需要同时满足：

前态空集成立：实际 S0 中没有原 Episode 的合格执行路径；

形成合法：每一个 f
i
	​

 都由有权主体实施或批准；

Episode 不变：Q、V0、必要 Principal、Authority 未发生未经分叉的语义改变；

后态有实际路径：不是只生成了计划文本，而是存在可验证的执行路径；

因果成立：新增条件确实使路径首次合格；

成本成立：没有通过隐藏成本、风险转移、隐私披露或不可逆锁定制造伪价值；

Effect 与 Acceptance 成立：工作流完成、哈希一致或审批按钮变绿都不能替代现实 Effect 和有权主体的 Acceptance。

三、应当使用的结果分类，而不是二元“形成/未形成”

建议至少使用以下五类结果：

结果	含义
DISCOVERED_EXISTING	S0 中真实合格路径已经存在，只是系统此前不知道
RESTORED_OR_ACTIVATED	过去存在或预先具备的路径因临时关闭、故障、过期配置而不可用，现在被恢复
NEWLY_QUALIFIED	同一 Episode 下，通过真实条件改变，使此前不合格的执行路径首次合格
AUTHORIZED_NEW_EPISODE	主体合法改变了 Q、V0、Principal 或 Authority，形成新的 E′
UNRESOLVED_OR_UNKNOWN	缺少 authoritative truth，无法诚实判断

RESTORED_OR_ACTIVATED 不是坏结果，但它与首次形成新条件不同。否则启用一个早已购买、早已授权的功能，也会被包装成“创造了新可能性”。

四、澄清、重表示、培训等动作究竟何时算形成
动作	仅属发现/建模	属于真实形成	形成新 Episode
澄清	解释原来已经明确但系统误读的参数	有权主体补充了执行所必需、此前未作出的有约束力选择	改变成功标准、风险承受或价值底线
培训	人员本来已经具备能力，只是系统不知道	培训真实创造了此前不存在的技能或资格	改换为更简单任务以适应现有能力
工具获取	找到一件已经可用的工具	购买、部署、校准并授权使用新工具	改成不需要原工具精度的任务
权限	发现已有权限	新的有权授权、JIT 权限或批准实际生效	删除原本必要的审批或 Authority
任务重表示	暴露一条本来存在的路径	有权重构接口、工作包或契约，使新组合在制度上可行动	改写目标、验收口径或所需主体
伙伴匹配	找到候选人或列表	对方表达当前意愿、确认能力/产能并形成承诺	用另一个较低标准伙伴替代必要主体
风险与恢复	写了一份回滚文档	回滚、隔离、监控和恢复能力已部署并验证	允许更大风险或取消可恢复性要求

最容易被误报的是“任务重表示”。单纯把自然语言翻译成结构化形式通常只改变 M
t
	​

，并没有改变 W
t
	​

。只有当重表示是一个制度性、关系性或接口性的有权动作，从而真实增加了可承诺、可采购或可执行的动作，它才属于条件形成。

五、失败分类
A. 关于 S0 的错误

F1：Latent-path discovery

真实路径早已存在，系统只是后来找到了它。

F2：Restoration mislabeled as creation

恢复过期 token、重新启动既有服务、重新启用已有供应商，被包装成首次形成。

F3：Model absence ≠ actual absence

规划器或 LLM 没找到路径，却没有建立动作空间、市场和政策的闭包。

F4：Actual-policy miss

使用旧政策、错误机构规则、缓存 IAM 状态或非 authoritative 摘要。OPA 官方文档也明确说明，OPA 使用外部数据和政策副本进行决策，本身并不是政策或外部事实的 source of truth。
Open Policy Agent

B. Episode 漂移

F5：Goal dilution

降低质量、范围、时间或安全要求。

F6：Value-floor dilution

总效用看似提高，但某个受保护 Principal 的底线被牺牲。

F7：Re-representation drift

所谓“重新表示”改变了可接受结果集合，而不是语义保持的重构。

F8：Authorized-new-episode conflation

主体确实同意了变化，但系统仍把 E′ 的成功归到 E。

C. Principal 与 Authority 替代

F9：Invalid Principal substitution

用相似主体、代理人、顾问或协调器代替不可替代的必要 Principal。

F10：Authority impersonation

把建议、角色、管理员权限、模型推断或上级身份误当成具体事项的授权。

F11：Match treated as relationship

搜索结果、名录、历史能力或“有兴趣”被当作当前报价、产能保留、合同和责任承担。

D. 条件与因果错误

F12：Evidence substituted for capability

证书、声明、健康检查或测试通过被当成现实能力，反之亦然。

F13：Workflow green substituted for Effect

durable workflow 能可靠重试和恢复流程，但外部 Activity 仍可能执行多次、部分执行，或在完成后、记录前发生崩溃；因此必须有幂等键和 authoritative effect readback。
Temporal 文档
+1

F14：Causal overclaim

删除所谓关键干预后，路径仍然成立；或者真实原因是未记录的外部变化。

F15：Hidden condition cost

路径依赖未计入的金钱、时间、披露、锁定、风险或其他主体承担的外部性。

F16：Private-truth laundering

系统免费调用类似：

partner.is_willing()
supplier.has_capacity()
authority.will_approve()

的 oracle，却不模拟询问成本、披露、延迟、拒绝、策略性回答以及“回答不等于承诺”。

这是 G3 中最危险的伪闭环之一。

六、现有方法的实际覆盖
6.1 Planner、LLM 与 tool use

LLM 很适合：

从非结构化材料中提出缺失条件；

生成备选干预；

解释失败；

调用真实系统查询状态；

将文本问题转写为结构化模型。

ReAct 展示了交错推理和外部行动的基本范式；LLM+P 则让 LLM 把自然语言转换为 PDDL，再交给经典规划器求解。
arXiv
+1

不能继续沿用“LLM 根本不会规划”的固定结论。2023 年 PlanBench 的确发现当时模型在计划生成等能力上明显不足；但 2026 年一篇使用新生成 IPC 任务和计划验证器的预印本报告，部分前沿模型已能在该任务集上达到或超过经典 planner 基线。另一方面，2026 年 SokoBench 又观察到超过约 25 步后的显著退化，并发现即使接入 PDDL 工具，错误的空间表示仍会使求解器解决“错误的问题”。这些结果说明能力高度依赖任务表示、验证方式和问题分布，而不是一个简单的“能/不能规划”。
arXiv
+3
arXiv
+3
arXiv
+3

但即使 LLM 能完美规划，它仍不能单独证明：

观察到的是当前真实政策；

某个 Principal 的私人意愿；

某人有权做出承诺；

Q/V0 没被语义改写；

干预确实创造了新路径而不是发现旧路径。

判定：强候选生成器和模型构造器，不是独立的 G3 证明系统。

6.2 HTN、PDDL 与约束求解

HTN、PDDL、SAT/MILP/CP-SAT 非常适合：

任务分解；

前置条件和效果建模；

资源与时间约束；

选择最低成本形成条件；

判断在给定模型内是 FEASIBLE、INFEASIBLE 还是 UNKNOWN。

HDDL 为 HTN 规划提供了较统一的层次化描述语言；CP-SAT 可以明确返回 OPTIMAL、FEASIBLE、INFEASIBLE、MODEL_INVALID 或 UNKNOWN。
AAAI
+1

真正的瓶颈是 action model。规划研究本身也承认，现实世界动作前提和效果的人工建模困难且容易出错；安全 action-model learning 通常需要较强观察与分布假设，并可能以牺牲 completeness 换取 soundness。
arXiv

判定：在条件动作已经显式、真实且当前时，基本完整解决搜索问题；不能自行保证模型是真的。

6.3 Workflow

Temporal、Camunda/BPMN 等系统已经能很好地处理：

长时运行；

等待外部消息；

人工审批；

重试、超时和升级；

Saga 与补偿；

事件历史与故障恢复。

Camunda 可以将人工任务、自动任务、等待、错误处理和补偿放在同一流程中；Temporal 可以通过持久化事件历史在 worker 崩溃后重放和继续。
Temporal 文档
+3
Camunda 8 文档
+3
Camunda 8 文档
+3

但 workflow 的基本输入仍是一个已经设计好的过程。它不会自动回答：

需要创造哪种新条件；

哪个新伙伴值得形成关系；

原任务是否已被改写；

流程完成是否等于现实 Effect；

为什么这次干预是路径首次出现的原因。

判定：形成轨迹的优秀执行层，而不是开放世界的形成发现层。

6.4 市场、名录与伙伴匹配

市场和资格名录能显著缩小候选集。NIST MEP Supplier Scouting 会根据具体技术需求寻找具有相应能力和商业兴趣的制造商；其官方流程通常在 30–45 天内返回候选结果。
NIST

但候选匹配与关系形成之间还隔着：

当前产能；

具体 scope；

报价和交期；

NDA 与数据披露；

客户批准；

合同；

capacity reservation；

责任、赔偿和恢复安排。

判定：解决 discovery，部分支持 formation，但不能把列表命中直接算成新路径。

6.5 人类设计与制度

人类仍然最擅长：

发现动作模型里根本不存在的新干预；

识别组织内的隐性约束；

谈判；

设计新工作包和接口；

形成制度、伙伴与信任；

判断何时应当诚实地 fork 为 E′。

其缺点是：

成本高；

结果不稳定；

容易在口头协商中偷偷降标；

证据链和可重复性较弱；

容易把“大家觉得可以”误作 Authority 已完成。

判定：开放世界最强基线之一，必须进入实验，而不是只拿 AI 系统相互比较。

6.6 强中心

若一个中心实体同时满足：

合法拥有或控制所有关键资源；

可以合法授予所需权限；

能代表全部必要 Principal；

拥有当前完整政策和真实状态；

条件动作已进入规划模型；

那么经典规划、约束求解和 workflow 已足以解决绝大多数 G3。

这是最强的 no-new-protocol 反例。

强中心失败的地方不是算力，而是其控制权是否真实存在。当某个 Principal 的同意不可被代行、供应商意愿私有、监管审批独立时，中心协调者不能通过系统设计把这些 Authority 抹掉。

七、最强成熟组合

目前最有竞争力的 no-new-protocol 方案是：

版本化 Episode 对象

固定 I、Q、V0、P、A；

所有语义变化必须生成差异并由 owner ratify；

实质改变自动 fork E′。

authoritative state connectors

IAM、合同、政策库、市场、供应商、审批系统；

每项事实记录来源、版本、时间、有效期和是否 binding；

OPA 等只做判定，不伪装成事实源。
Open Policy Agent

LLM + 人类的 condition generator

生成培训、工具、伙伴、授权、重构和恢复候选；

不自行认定候选已经生效。

HTN/CP/SAT planner

检验前置条件、顺序、资源和成本；

求最小或 Pareto 有效的条件集合。

market/registry/procurement connectors

候选发现；

当前 scope、资格和产能验证；

报价、承诺、合同、capacity reservation。

durable workflow

执行审批、采购、培训、授权、等待、补偿和升级；

记录每个 Authority 的真实动作。

Effect 与 Acceptance readback

从执行系统、质量系统、监管系统和 owner 获取权威回读；

不使用“workflow completed”作为最终 Effect。

formation evaluator

检查 S0 空集；

检查 Episode 不变；

检查 Authority；

运行反事实和移除测试。

这是一套组合架构，不要求新的通信协议。

八、三个真实任务
8.1 任务 A：NIH 受控基因组数据分析
固定 Episode

一个研究团队希望：

对指定受控数据集；

执行指定研究问题与分析方法；

在指定期限内；

输出允许公开的聚合结果；

不把数据、衍生数据或受限制模型暴露给未授权主体。

S0

研究问题已经明确，但可能缺少：

approved DAR；

Institutional Signing Official；

符合要求的安全环境；

对应 Data Use Limitation 的研究用途陈述；

获准用户培训；

外部合作者自己的访问批准。

NIH 的 DUC 明确把 PI、Requester institution 和 NIH 作为协议当事方，并规定外部机构的科学合作者通常必须提交自己的 DAR；DAC 的决定主要依据研究用途是否符合提交机构设定的数据使用限制。
NIH Grants
+1

截至当前规则，新签或续签协议自 2026 年 2 月 25 日起需要遵循 NIH 当前 controlled-access security standards。因此使用旧安全基线可能产生真实的 actual-policy miss。
NIH Grants

合法形成轨迹

对研究用途声明作语义保持的澄清；

从 authoritative dataset page 获取当前 DUL；

配置并验证合规计算环境；

完成培训；

PI 和 Institutional Signing Official 签署；

DAC 批准；

为外部合作者建立其自己的合法访问；

执行分析并验证输出；

由有权主体接受结果。

对抗错误

将研究问题改成更容易通过 DUL 的问题：AUTHORIZED_NEW_EPISODE。

让外部合作者使用 PI 凭据：INVALID_AUTHORITY_SUBSTITUTION。

把 DAR 已提交当成路径已形成：审批尚未生效。

将数据输入公共生成式 AI：NIH 已明确禁止把 controlled-access data 或衍生数据交给未授权公共生成式 AI，也禁止分享用这些数据训练的生成式模型和参数。
NIH Grants

实际已有另一份有效 DAR，却因系统记录缺失被误报为新形成：DISCOVERED_EXISTING。

把 DAC 是否批准做成免费 oracle：无效实验设计。

现有组合覆盖

政策流程、身份、审批和安全环境已有成熟制度。残余主要是：

自动保持 Episode 语义；

区分申请、批准、访问、Effect；

识别外部合作者的独立 Authority；

对形成因果进行验证。

8.2 任务 B：航空零件关键工艺与供应关系形成
固定 Episode

制造一个指定图纸版本的航空零件，要求：

固定材料、尺寸、公差和关键工艺；

指定交期和成本底线；

必要的客户或设计 Authority；

指定工艺 scope 的供应商资格；

FAI 和质量证据。

AS9102C 的用途就是规定 First Article Inspection 的执行和记录要求。
SAE国际
+1

S0

主制造商可能具备大部分加工能力，但缺少：

指定 heat treatment、chemical processing、NDT 等关键工艺；

当前 scope 内的合格供应商；

可满足交期的产能；

客户 source approval；

检测工具；

FAI 证据。

Nadcap 是航空、国防和航天关键工艺的行业管理型 accreditation 体系，覆盖热处理、无损检测、焊接、化学处理等过程。
P-R-I
+1

合法形成轨迹

精确拆解需要外包的工艺 scope；

使用 NIST MEP、QML 或客户批准名录寻找候选；

验证 accreditation 的具体工艺、材料、地点和有效期；

获取当前报价、产能和交付承诺；

完成 NDA、图纸披露和技术澄清；

获得客户或设计 Authority 的 source approval；

签约并保留产能；

执行样件、工艺验证和 FAI；

建立备选供应商、返工和恢复机制；

完成实际生产和 Acceptance。

eAuditNet 的官方 FAQ 明确指出，Online QML 可以检索 Nadcap approved suppliers，但 QML 不提供供应商证书副本，仍需直接联系供应商确认。
eAuditNet

对抗错误

供应商有 Nadcap，但 scope 不覆盖当前材料或过程。

供应商名录有效，但当前没有产能。

NIST scouting 返回“有能力、有商业兴趣”，系统把它当成合同。

使用价格较低但未获客户批准的工厂：invalid substitution。

客户同意降低规格：合法，但属于 E′。

原来已有获批供应商，只是采购数据库没同步：发现，不是形成。

把供应商的非约束性回复当成 capacity reservation。

现有组合覆盖

资格名录、供应商 scouting、采购、合同、质量体系和 workflow 已覆盖大部分流程。真正未被统一解决的是：

从“候选”到“当前可依赖关系”的状态跃迁；

私有产能和意愿；

客户 Authority；

多组织之间的 Episode 与条件证据一致性。

8.3 任务 C：带审批和恢复约束的生产补丁部署
固定 Episode

部署指定 patch 或配置版本，要求：

固定 commit/artifact；

固定生产环境；

固定截止时间；

满足 availability/error budget；

服务 owner 与安全 Authority 的批准；

不使用长期云密钥；

具有已测试的 canary 和 rollback；

完成后由监控和业务系统确认 Effect。

S0

补丁存在，但当前没有合格部署路径，因为：

操作者没有生产权限；

workflow 没有必要审批；

缺少短时凭证；

没有 canary；

没有自动回滚和监控。

合法形成轨迹

配置 deployment environment；

配置 required reviewers 和防止 self-review；

建立 GitHub OIDC 到云角色的信任；

配置 JIT temporary elevated access；

配置 canary、告警和 rollback；

运行 staging 验证；

获得当前批准；

部署并进行 authoritative service readback；

owner 接受。

GitHub environments 支持 required reviewers 和禁止 self-review；但其原生规则中，即使配置多个 reviewer，默认只需其中一个批准。因此，如果 Q 要求“服务 owner 与安全 owner 双批准”，仅配置一个 GitHub required-reviewer gate 并不充分，需要额外的独立 gate 或 custom protection rule。
GitHub Docs

GitHub OIDC 可以让 workflow 获取只在单个 job 内有效的短期云 token，而无需长期云凭证；AWS 将 temporary elevated access 定义为对特定任务、特定时间的申请、审批和追踪。
GitHub Docs
+1

AWS CodeDeploy 支持在失败或监控阈值触发时自动部署上一个已知良好版本。
AWS 文档

对抗错误

使用硬编码 admin key：执行上可行，但违反 Q。

incident commander 并非本服务的批准 Authority。

rollback 只存在文档，从未部署或测试。

通过关闭告警使部署“成功”。

延长 deadline：新 Episode。

emergency access 早已存在，只是系统不知道：发现或激活。

CI 显示完成，但服务实际未达到健康条件。

现有组合覆盖

这是成熟组合最可能完整解决的控制任务。若 LLM + IAM + CI/CD + workflow + policy + telemetry 仍不能解决，应首先查工程集成、模型或实验设计，而不是据此主张需要新协议。

九、统一指标
9.1 Newly Qualified Path precision / recall

一次 NEWLY_QUALIFIED 声明只有同时通过以下门槛才计为真阳性：

实际 S0 无合格执行路径；

同一 Episode；

条件动作合法；

后态路径实际成立；

Authority 未替代；

因果测试通过。

NQP-Precision=
全部形成声明
有效形成声明
	​

NQP-Recall=
全部真实形成案例
被正确识别的真实形成案例
	​


在高风险领域，precision 应是主指标，因为一次“假形成”可能意味着非法访问、错误生产或越权部署。

9.2 Actual-policy miss

分别报告：

false-allow：系统认为允许，当前 authoritative policy 实际不允许；

false-deny：系统错误放弃一条合法路径；

stale-policy：使用过期版本；

wrong-authority：查询了无权作出决定的主体；

unjustified-known：应为 UNKNOWN，却输出了确定结论。

9.3 Invalid substitution

分别统计：

Principal replacement；

Authority replacement；

resource/specification replacement；

acceptance replacement；

coordinator self-approval。

不能只统计最终是否“任务完成”。

9.4 Authorized new episode

将 NEWLY_QUALIFIED 与 AUTHORIZED_NEW_EPISODE 作为独立分类，报告 macro-F1。

系统正确地说：

原 Episode 不可行；主体已合法批准 E′；下面开始新的 Episode。

这是成功的治理行为，不应被当成失败，也不能冒充 G3 成功。

9.5 价值保留

建议使用：

VP=1⟺∀p,d,V
p,d
	​

≥V
0,p,d
	​


并要求：

不存在未经批准的风险转移；

不用一个 Principal 的收益抵消另一个 Principal 的底线损失；

所有新成本和 disclosure 均进入核算；

owner 对关键价值维度进行 ratification。

9.6 条件成本

形成成本应是向量：

K(δ)=⟨money,calendar time,human labor,disclosure,operational risk,irreversibility,lock-in,authority burden,externality⟩

优先比较 Pareto frontier。若确实需要单一分数，权重必须在实验前由 Episode owner 固定，不能在看到结果后调权。

9.7 因果移除

定义：

Reach
E
	​

(W)=1[Π
E
	​

(W)

=∅]

干预集合 D 是充分的，当：

Reach
E
	​

(do(D),W
0
	​

)=1

它是最小充分集合，当所有真子集 D
′
⊂D 都无法形成路径。

现实中常有冗余原因：例如两个供应商中的任意一个都足以形成路径。因此不应要求“每个单独步骤都必要”，而应识别一个或多个最小充分干预集合。实际因果研究也强调反事实、 contingency 和 minimality，而不只是简单的单变量删除。
康奈尔大学计算机系

建议报告：

sufficiency pass；

minimality pass；

claimed-essential removal pass；

nonessential removal stability；

least-cost minimality gap。

十、反事实与 adversarial test
10.1 Latent-path pair

两个案例拥有相同目标材料：

世界 A：S0 中已有合格路径；

世界 B：必须增加一项新权限才有路径。

测试系统是否会把 A 的发现也称为形成。

10.2 Policy-flip pair

静态材料完全相同，但 authoritative policy 版本不同。

正确系统必须实时查询版本；无法查询时返回 UNKNOWN，而不是依赖语义猜测。

10.3 Principal/Authority pair

行动、能力和结果完全相同，只改变批准者是否具有该事项的 Authority。

这能检测系统是否把“有管理员权限”“职位更高”或“是协调者”自动等同于有权批准。

10.4 Semantic-drift pair

两种澄清文本表面相近：

A 只补充执行参数；

B 实际降低了质量、时限或安全要求。

测试 Episode equivalence，而不是关键词相似度。

10.5 Authorized-fork pair

同一个 Q 变化：

A 未经 owner 批准；

B 由 owner 明确批准。

A 是 invalid drift，B 是合法 E′。两者都不是原 Episode 的 newly qualified path。

10.6 Private-truth pair

系统收到完全相同的供应商资料：

A 供应商愿意且有当前产能；

B 不愿意或无产能。

若意愿不可从现有观察中得知，没有任何算法能从静态 packet 中正确区分。正确动作只能是：

发出正式询问或 offer；

承担披露、延迟和被拒绝的成本；

获得有约束力的回复；

或返回 UNKNOWN。

这个测试能直接淘汰“把 private truth 包装成免费 API”的方案。

10.7 Recovery-theatre pair

两套系统都有 rollback 文档：

A 的回滚经过 staging 和故障注入验证；

B 只有说明文档。

只有 A 真正改变了路径的风险资格。

10.8 Redundant-cause pair

培训和新工具均可独立解决同一缺口。系统若声称两者都“不可缺少”，因果模型就是错的。

十一、从同一原始材料开始的 held-out 实验
11.1 两条实验轨
Track R：Raw-material track

所有系统得到完全相同的原始材料：

Intent 与 owner 确认；

邮件、工单、政策文档；

当前资产和权限清单；

市场或供应商记录；

组织角色；

工具描述；

预算与时间限制。

不提供人工整理的 PDDL、HTN 或约束模型。

该轨测试：

条件识别；

模型获取；

语义保持；

authoritative query 决策；

规划和执行。

Track M：Model-controlled track

向所有系统提供同一份经专家验证的：

Episode 对象；

状态变量；

task actions；

formation actions；

authority topology；

policy predicates；

cost model。

该轨只测试：

搜索；
-优化；

分类；

工作流执行；

因果判定。

两轨缺一不可。否则模型抽取失败会被错误归因于 planner，或者人工形式化的正确答案会掩盖真实世界建模问题。

11.2 数据规模

建议：

9 个开发案例，不计分；

36 个 held-out root episodes：

NIH/受控数据 12 个；

制造与供应关系 12 个；

生产部署 12 个。

每个 root episode 构造 6 个单变量反事实变体：

真形成；

latent path；

restoration；

invalid substitution；

authorized new episode；

policy/private-truth trap。

总计 216 个配对评测 episode。

held-out 应按机构、政策模板、供应链和系统环境切分，不能随机切段落，否则会发生模板泄漏。

11.3 实验组

Frontier LLM + tools；

LLM + classical planner/CP；

专家建模 HTN/CP；

workflow + rule/policy engine；

market/registry + workflow；

人类领域专家团队；

合法强中心 upper bound；

完整成熟组合。

强中心不能与其他组假装拥有同等 Authority。它应被单独标记为“在合法集中控制假设下的上界”。

11.4 查询规则

所有对 Principal、Authority 和私有系统的查询都必须是一等动作，记录：

请求者；

接收者；

披露内容；

时间；

成本；

是否有义务回答；

CURRENT / REFUSED / UNKNOWN / STALE；

回答是 advisory、informational、approval 还是 binding commitment；

有效期和撤销条件。

禁止为任何实验组提供无限、免费、永远正确的 private oracle。

11.5 现实执行层级

为兼顾可控性和真实性，可以分三层：

L1：可重放封闭环境

云部署 sandbox；

模拟 IAM；

镜像政策库；

模拟供应和审批系统。

用于大规模反事实与条件移除。

L2：真实 authority shadow mode

使用真实政策和真实 reviewer；

形成真实审批判断、报价或资格审查；

但不一定执行高成本最终动作。

L3：真实 live subset

至少选择少量案例完成：

真实 scoped approval；

真实 supplier commitment 或 capacity reservation；

真实 staging/production effect；

真实 owner Acceptance。

仅靠“专家认为这个计划应该可行”不能证明 newly qualified path。

对于培训、认证和长期合同等不可逆干预，不能粗暴地在真实世界中做删除实验。可以使用：

S0 环境克隆；

匹配分支；

预先建立的 shadow case；

经独立专家确认的结构因果模型。

11.6 Ground truth 和盲评

每个 root case 由以下人员在实验前建立 sealed truth：

domain owner；

对应 Authority holder；

独立技术评审；

实验 red team。

系统输出必须包括：

结果类别；

Episode 版本；

S0 absence claim 及边界；

条件干预；

每个 Authority 的依据；

形成成本；

后态执行路径；

Effect readback；

Acceptance；

反事实和 causal removal 结果。

评审者在不知道实验组的条件下打分。

11.7 主要终点

建议主终点为：

固定条件成本预算下的 NQP precision。

次级终点包括：

NQP recall；

actual-policy miss；

invalid substitution；

authorized-new-episode macro-F1；

value preservation；

形成时间与人类负担；

最小充分干预成本；

causal removal pass；

UNKNOWN/REFUSED 的正确使用率。

11.8 通过两轨定位 residual

实验结果应按以下方式归因：

结果	更可能的问题
Raw 失败、Model-controlled 成功	文档理解、模型获取、状态连接器
两轨都无法规划	planner、约束表达或搜索
能规划但无法实施	workflow、工具、采购或人类流程
实施成功但误报形成类别	Episode/因果判定
反复发生 policy miss	source-of-truth 与版本治理
只在私有意愿上失败	合法查询、关系形成与拒绝处理
强中心成功、独立主体组合失败	跨 Authority 协调 residual
人类和完整组合都失败	任务本身可能不可形成或闭包错误

只有这样才能知道值得创新的是 planner、模型获取、连接器、治理对象，还是根本不存在可解决的信息条件。

十二、哪些已经解决，哪些没有
已经被成熟组合基本解决
1. 给定完整动作模型后的条件搜索

HTN、PDDL、SAT、MILP、CP-SAT 已经能够处理：

多步条件获取；

资源和时间；

顺序和依赖；

最低成本或可行解。

2. 已知形成流程的可靠执行

BPMN、Camunda、Temporal、Saga、人类任务和 IAM 已经能够执行：

申请；

等待；

审批；

授权；

重试；

补偿；

超时和升级。

3. 单组织、合法强中心环境

生产部署任务很可能不需要任何新的 G3 协议。缺少的通常是正确集成和验证。

4. 候选供应商或伙伴发现

市场、资格名录、NIST scouting 等已经能显著缩小候选集。

仍未被充分测量

S0 实际无路径，而非模型没找到路径；

自然语言澄清和重表示是否保持 Q/V0；

Principal 与 Authority 是否在跨系统中被偷偷替代；

候选匹配何时真正变成有约束力的关系；

当前政策、产能和意愿的 query/refusal/latency 成本；

冗余条件下的因果最小性；

形成路径与 authorized new episode 的稳定区分；

Effect 和 Acceptance，而非工作流完成；

同一评测同时跨数据、制造和 IT 三个真实领域。

所以当前最严重的空白首先是评测空白和证据空白，还不能直接推出协议空白。

十三、真正值得创新的 residual

只有在完整成熟组合与人类基线跑完后，以下 residual 仍显著存在，才值得单独创新。

Residual 1：Episode 完整性与自动分叉

系统能否对澄清、重表示和协商结果做语义差异分析，并稳定判断：

同一 E；

非语义修订；

需要 owner ratification；

必须 fork E′。

这可以先实现为版本对象、差异摘要和 owner gate，不必先成为网络协议。

Residual 2：Authority-grounded condition model

每个条件不仅有布尔值，还应带：

owner；

source of truth；

scope；

effective time；

expiry；

acquisition action；

disclosure cost；

refusal possibility；

delegability；

binding level；

revoke path。

如果现有 IAM、workflow 和合同对象无法跨组织表达这些内容，才可能出现标准或协议 residual。

Residual 3：开放世界 formation-action acquisition

LLM、人类或其他系统能否发现模型中原本没有的合法条件动作，例如：

新培训路径；

新工具；

新制度接口；

新合作结构；

新恢复机制。

这与在既有 action set 上规划不同。但新动作必须经 Authority 和真实执行验证，不能由模型自证。

Residual 4：Formation witness

系统是否能生成可独立审计的证据：

S0 absence boundary；

Episode invariance；

condition trace；

policy/authority snapshots；

post-condition readback；

actual Effect；

owner Acceptance；

minimal sufficient intervention set。

这更像新的评价与证据对象，而不必然是新的通信协议。

Residual 5：有成本、有拒绝权的私有事实获取

当产能、意愿、风险偏好和批准判断属于独立 Principal 时，系统必须处理：

不可查询；

被拒绝；

延迟；

部分披露；

非约束性回答；

条件承诺；

撤销。

如果所有竞争方案都只能靠免费 oracle 才闭环，这才是可信的 residual。

十四、最强反例与终止条件
反例一：形成问题退化为普通规划

一旦所有培训、授权、采购、关系、恢复动作都进入完备 action model，G3 就是扩展动作集上的规划和执行。

这意味着新研究不能只把这些动作换个名字写成“formation operator”，就声称获得了新的问题类别。

反例二：合法强中心完整解决

若中心拥有全部 Authority 和完整状态，成熟 planner + workflow 完整解决问题，则 G3 的价值不能建立在“任何协调都必须去中心化”的预设上。

反例三：观察不可区分

两个世界对系统的全部可用观察完全相同，但某个独立主体的私人意愿相反，并且系统没有权利查询。

此时不存在能够始终正确区分两世界的算法。唯一正确结果是 UNKNOWN，或发起一次合法、带成本的询问。

这说明部分失败是信息和 Authority 边界，不是智能不足。

研究终止条件

若完整成熟组合在 held-out live track 中：

与强中心在可比任务上接近；

与人类专家相比没有显著 NQP recall 损失；

actual-policy miss 和 invalid substitution 接近零；

能正确 fork 新 Episode；

条件成本和人类负担可接受；

causal witness 稳定通过；

那么应接受结论：

G3 在所测边界内已被现有技术组合解决，没有充分理由发明新的通用协议。

反过来，只有某个 residual：

在 Raw 和 Model-controlled 两轨中都持续存在；

不能由补连接器、补政策源、补 workflow 或补人类 gate 消除；

在多领域 held-out 案例中复现；

新方案能提高 newly qualified path 的 precision/recall；

不增加 Authority 替代、政策错误、价值损失和私有 oracle 依赖；

它才值得成为独立创新。

最终判断

G3 最合适的研究名称不是泛化的“可能性创造”，而是：

Authority-grounded Qualified-Path Formation under Episode Invariance
在 Episode 不变和真实 Authority 约束下，经合法条件干预形成合格路径。

它的计算核心在封闭世界里并不新：规划、约束、workflow、IAM、市场和人类制度已经覆盖很多部分。

真正可能具有原创性的部分，是把以下区分压进同一套可证伪实验：

actual absence 与 model absence；

discovery、restoration、formation 与 new episode；

representation change 与 world change；

candidate matching 与 binding relationship；

permission bit 与 Authority；

workflow completion 与 Effect/Acceptance；

intervention correlation 与 causal formation；

private truth 与合法、带成本、可拒绝的查询。

因此，当前最合理的下一步不是先写一套 G3 协议，而是先实现：

版本化 Episode 与分叉判定；

三域 held-out benchmark；

authoritative state/query 层；

mature full-stack baseline；

formation witness 与 causal-removal evaluator。

实验之后，可能得到两种同样正向的结果：要么成熟组合已经解决问题；要么只剩一个足够窄、足够真实、无法再被 planner、workflow、强中心或人工流程吸收的 residual。

