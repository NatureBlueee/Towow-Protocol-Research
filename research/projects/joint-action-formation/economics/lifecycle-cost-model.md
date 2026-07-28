# 低频异构关系的全生命周期成本模型

状态：`CANDIDATE RESEARCH MODEL`  
作用域：`PRB-JOINT-ACTION-FORMATION / v1-candidate`  
更新时间：2026-07-28

## 一、成本校正

本研究不把一次 Agent 调用消耗一美元还是两美元当成核心成本。机器推理、检索、存储和网络
支出应记录，但当前主要比较对象是：

> 一个此前没有规则、字段、合同、角色、审批路径和验收标准的低频异构关系，要被组织理解、
> 决定、实现并变成可重复运行规则，需要付出多少真实组织成本。

主要成本通常体现为：

- 多团队识别问题、同步上下游和反复开会；
- 高语境员工与负责人的认知时间；
- 等待法务、采购、数据、技术、业务和管理层作出判断的日历时间；
- 平台字段、合同、审批、权限、接口、证据和异常流程的建立；
- 因等待、错误拒绝、过早承诺、返工或项目错失产生的机会损失；
- 关系形成后维持、验证、处理争议、恢复和重开的成本。

用户在 2026-07-28 提出的工作观察是：大型集团中的新型上下游合作可能需要三四个团队，
半个月到三个月才能完成规则与协作闭合。这是需要进入真实案例测量的研究输入，不是当前已经
由独立数据验证的频率结论。

## 二、完整成本账本

对关系 episode \(e\)，定义：

\[
\begin{aligned}
C_{life}(e) =\;& C_{attention}+C_{org}+C_{meeting}+C_{delay}
+C_{opportunity}\\
&+C_{disclosure}+C_{search}+C_{relation\_modeling}
+C_{rule\_formation}\\
&+C_{contract}+C_{approval}+C_{integration}
+C_{verification}\\
&+C_{error}+C_{governance}+C_{recovery}+C_{compute}.
\end{aligned}
\]

其中：

- \(C_{attention}\)：必须由高语境人员完成的理解、解释、例外和责任判断；
- \(C_{org}\)：跨部门、跨企业、跨专业和跨权威主体的组织协调；
- \(C_{meeting}\)：准备、参与、纪要、追问和重新确认的人员时间；
- \(C_{delay}\)：从提出到真实处置的日历等待；
- \(C_{opportunity}\)：等待、晚拒绝、错配和资源占用造成的机会损失；
- \(C_{relation\_modeling}\)：形成问题、参与者、角色、动作、约束、风险和接受标准；
- \(C_{rule\_formation}\)：把关系模型固化为平台规则、字段、合同、审批和异常处理；
- \(C_{integration}\)：账户、数据、工具、目标系统、身份和证据链的接入；
- \(C_{verification}\)：能力、授权、Effect、Adoption、Acceptance 和 Settlement 的验证；
- \(C_{error}\)：False Commit、False Reject、Premature Commit、Late Reject、越权 Effect、
  未接受采用和隐藏外部性；
- \(C_{governance}\)：授权维护、挑战、争议、问责、审计和制度认知负担；
- \(C_{recovery}\)：漂移、撤销、失败、退出和局部或全局重开；
- \(C_{compute}\)：模型、RAG、算法、存储、网络和机器执行支出。

\(C_{compute}\) 必须保留，但不能替代前十一类成本，也不能因为容易计量就成为研究的主要
优化目标。

## 三、智能判断负担不是数据量

本研究需要区分：

- **数据处理量**：读取、检索、聚合或变换多少数据；
- **智能判断负担**：需要对多少个此前未稳定定义、相互依赖且可能冲突的差异作出高质量判断；
- **规则形成负担**：把这些判断变成可执行、可验证、可维护制度所需的工作；
- **复用程度**：一次判断或规则能否在后续关系中直接复用。

RAG 主要降低 \(C_{search}\)，并可能降低部分 \(C_{attention}\)。摘要和专用算法可以降低
已知关系语法中的计算成本。但它们不自动解决：

- 新关系的参与者和角色尚未确定；
- 各主体的局部语义、权威、风险与接受标准不一致；
- 需要创建新权限、伙伴、工具、资源或目标域条件；
- 某项主张只能由本地权威事实源作证；
- 执行结果仍需目标域 readback 和 Principal 接受；
- 关系成功后怎样编译、失败后怎样局部重开。

所以决定中心系统负担的不是原始字节数，而是关系新颖性、异构性、开放维度、权威分散、
信息局部性、依赖耦合、漂移率，以及不可复用判断的数量与承重程度。

## 四、决策能量假说

用户提出：足够智能的判断必然要求系统投入相称“能量”，该投入可以表现为模型、算法、
专用训练、合同、制度、组织会议、人工解释或错误风险。

本研究暂时将其写成一个可检验的会计假说，而不是热力学定律：

> 对一个此前未被规则覆盖的异构关系，消除关键 Unknown、形成权威一致的可执行路径并验证
> 现实结果所需的判别工作不会凭空消失。系统只能承担它、把它转移给其他主体、容忍更高错误，
> 或将已完成的判断编译复用。

定义未编译判断负担：

\[
J(e)=\sum_{k=1}^{m} w_k \cdot d_k \cdot (1-r_k),
\]

其中 \(d_k\) 是第 \(k\) 项 material judgment 的难度，\(w_k\) 是其对权威、风险和结果的
承重程度，\(r_k\) 是可从既有规则安全复用的比例。该式目前只是一种测量结构；权重必须从
真实案例和错误后果校准，不能由研究者主观赋值后宣称为物理量。

## 五、中心、平台、通爻与人类的生命周期曲线

### 专用平台

\[
C_{platform}(r,N)=F_{schema}(r)+F_{institution}(r)+F_{integration}(r)
+N c_{run}(r)+C_{change}(r).
\]

平台在关系类型 \(r\) 稳定且高频时可能最好：首次规则形成固定成本高，但边际运行成本低。

### 通用中心 Agent

\[
C_{central}(r,N)=F_{central}+N(c_{context}+c_{judgment}+c_{verification})
+C_{authority}+C_{drift}.
\]

中心可以复用模型、RAG、工具和组织基础设施，不能被假设为每次从零开始。但若关系低频、
跨域且事前不可枚举，它仍可能反复支付上下文获取、关系语法形成、局部权威确认和验证成本。

### 通爻形成—编译路径

\[
C_{towow}(r,N)=\alpha F_{shared}+F_{formation}(r)+F_{compile}(r)
+N c_{compiled}(r)+pNr_{reopen}.
\]

\(\alpha F_{shared}\) 是共享形成基础设施分摊；\(F_{formation}\) 是该关系首次形成成本；
\(F_{compile}\) 是稳定子图编译成本；\(p\) 是 Defeater 概率，\(r_{reopen}\) 是重开成本。

档案已有：

\[
Saving(N)=N(f-c)-F_0-pNr.
\]

v1 需要进一步检验：通爻是否真的降低 \(F_{formation}\)，还是只把
\(F_{schema}+F_{institution}+F_{integration}\) 分散到多个 Agent 和 Principal。

### 人类经纪

人类可能在极低频、高语境和社会合法性强的场景中最好。其成本不能只按工资计算，还包括
等待、容量上限、知识不透明、交接、错误和机会损失；其隐性知识与现实信任优势也不能删除。

## 六、架构不是标签，而是 Router 的输出

每次关系与每个子问题都应按以下变量选择机制：

```text
relation_novelty
heterogeneity
open_dimensions
authority_topology
information_locality
privacy_and_rights
institutional_sufficiency
standardization
expected_recurrence
need_for_high_context_judgment
irreversibility
uncertainty_and_drift
resource_coupling
coordination_cost_budget
```

Router 输出的不是“中心化”或“去中心化”标签，而是：

\[
Plan=\langle mechanisms, transitions, authority\ gates,
effect\ gates, compile\ conditions, fallback \rangle.
\]

同一关系可以：

- 用中心索引发现候选；
- 用本地权威形成非标准条件；
- 用人类处理高语境与争议；
- 用中心优化器调度资源；
- 用确定性平台执行稳定支付和凭证；
- 把稳定子图编译为低成本服务；
- 在新 Defeater 出现时只重开依赖部分。

## 七、待检验假说

### H-COST-1：规则形成而非 token 是主要成本

在真实低频异构合作中，模型调用成本只占 \(C_{life}\) 的小部分；高认知人力、组织协调、
日历等待、规则建立、集成、错误和机会损失决定机制差异。

反向结果：机器成本成为主要成本，或其变化与总处置成本高度同步。

### H-COST-2：共享形成基础设施降低新关系边际成本

通爻能够跨行业复用身份、Mandate、边界查询、RelationVersion、证据、Effect、Acceptance、
编译与重开基础设施，使每类新关系不必重新建设完整平台。

反向结果：每类关系仍需要与专用平台相当的会议、建模、合同、审批和集成。

### H-COST-3：中心负担由不可复用判断密度决定

在数据量相近时，低频、异构、开放维度、跨权威且高漂移的任务使中心机制承担更高的
上下文获取、判断和规则形成成本；标准、高频、低漂移任务则可安全 Collapse。

反向结果：通用中心在同等权威、隐私和验证约束下，以相同或更低判断负担跨任务稳定泛化。

### H-COST-4：稳定关系可以编译

形成后的稳定子图可以转为中心、联邦或混合的确定性运行机制，降低后续高认知时间、披露和
协调成本。

反向结果：稳定边界无法可靠识别，编译导致陈旧授权、错误继承或频繁全局重开。

### H-COST-5：Router 优于固定立场

按关系阶段和子问题组合中心、联邦、平台与人类机制，比固定“全中心”或“全去中心”在
真实处置时间、错误、权威保真和生命周期成本上更好。

反向结果：一个固定机制在现实分布中持续达到同等保真度与更低总成本。

## 八、现实数据最低要求

每个案例至少记录：

- 涉及团队、角色、Principal 和 Authority Locus；
- 从首次提出到真实 Commit/Reject/Defer 的日历时间；
- 会议次数、参与人数、准备和跟进时间；
- 高认知判断清单及实际承担者；
- 新建或修改的平台字段、合同、审批、权限、接口和证据；
- 等待、返工、晚拒绝、错误承诺和机会损失；
- 模型、RAG、算法和机器执行支出；
- 首次形成、编译、每次复用和重开的成本；
- 真实 Effect、Adoption、Acceptance、30/90 天后悔与 reopen；
- 同一事项在强中心、成熟平台、人类经纪和 Router 方案下的反事实或 matched baseline。

## 九、来源与边界

档案中的直接基础：

- `Towow_R8_OPC_Constructive_Closure_v1.1/paper/...正式论文_v1.1.md`：
  多机制 Router、CollapseSafe、协调成本结构、错误成本、Compiled World 与强基线；
- `Towow_A2A_Independent_Research_v0.3/00_EXECUTIVE_FINDINGS.md`：
  中心在 CollapseSafe 安全角落净值更高，以及非标准关系形成与静态平台的区分；
- `research/projects/a2a-reconstruction/02_derived/large-docs/monograph-v1.1/29_25-经济模型...md`：
  对原始 v1.1 经济章节的可定位派生视图。

当前没有真实组织样本证明“三四个团队、半个月到三个月”是一般分布，也没有证明
\(F_{formation}\) 已低于平台规则建立成本。该观察与上述假说必须进入案例采集，而不能作为
通爻优势的既定前提。
