## 核心结论

Wave010 目前没有发现一个稳定、必须由新 G5 机制解决的 residual。

更准确地说：

- Wave009 已经给出真正的正结果：在可信父进程、显式结构化语义、单进程原子 Reservation 等限定下，强中心 B0 和成熟组件组合 B5 都完成了 G2、G5 与 integration `24/24`；11 个 residual 检查也全部通过。成熟栈闭合该模型就是成功，不应再创造“通爻专属缺口”。证据见 [Wave009 Second Return](</Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/WAVE-009-SECOND-RETURN.md:122>) 和 [crossed-square README](</Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-009-g2-g5-crossed-square/README.md:199>)。
- Wave010 M01 尚未跨越“设计了四份 authority JSON”到“四个真实 Authority owner 独立签发、拒绝、撤销并承担后果”的门槛。目前仍是 `scoreable-pair freeze candidate`，scoreable episode、方法、runner、run 都是零或未运行，见 [M01 AUDIT-002](</Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-010-x1-m01-freeze-bundle-v0/AUDIT-002.md:4>)。
- 因此现在能说的是：**成熟组合已闭合有限结构化模型；是否闭合真实跨域任务尚未运行。** 当前 residual 是待检验的跨合同断点，不是已经发现的新协议对象。

三条独立母线均已并行返回：A 重建非蕴含，B 比较成熟栈，C 构造时序、owner、Standing 和迁移攻击；以下是主线程综合，不以任何一条母线的共识代替证据。

## 一、实际任务矩阵

| 材料 | 实际状态 | 当前可支持的结论 | 主要误放 / 误拒风险 | 成为有效任务还缺什么 |
|---|---|---|---|---|
| T2 企业只读试点 | `ARCHIVAL_ANSWER_LEAKAGE_REPLAY` | 可检查完整设计链，但答案已暴露 | 预算批准被当作数据 Mandate；技术可行被当作训练授权；拒绝原方案被当作全部路径不可能 | 隐去 v1/v2、反例和答案，建立独立 oracle 后冷启动重跑 |
| T3 R7 | `EXECUTION_RESOURCE_REQUIREMENT_ONLY` | 只能说明执行资源需求 | 把资源清单误当 Authority 世界；没有分母却报告 coverage | 补 S0、主体、行为、owner、authority poststate 和 oracle；否则从 G5 分母移除 |
| T4 joint-bid | 冻结合成任务 | 可以做本地、结构化攻击 | capability/签名/portal receipt 被当 Commitment 或 Reservation；`UNKNOWN` 被当 incapable | 引入独立 owner/oracle、真实并发和未知 holdout |
| T6 mutation replay | 规格存在，base run/oracle 未建立 | 只能定义候选变异 | stale head、过期 handoff、重复 Reservation 被放行；短暂离线被误判为 revoke | 先产生独立 base trace，再运行 mutation 与依赖传播 |
| M01 四域 | freeze candidate，未运行 | 四种 AuthorityLocus 的候选拆分有价值 | 四个文件、四个字符串 key 被误称为四个真实 owner；X1 handoff 被误称为 attempt permit | 四个独立运行时 owner、独立密钥域、可拒绝接口、真实 head/receipt |
| Wave009 crossed square | 已运行的局部对照 | B0/B5 在限定模型内完整闭合 | 外推到真实 Principal、分布式线性一致性、自然语言或生产会误放 | 作为回归对照保留，不能冒充 Wave010 现实结果 |

任务真值修正的正典依据见 [TASK-TRUTH-CORRECTION-001](</Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/TASK-TRUTH-CORRECTION-001.md:12>)。

## 二、G5 必须保留的非蕴含

这些是现实差异，不意味着必须实现九个新协议对象：

- `Identity ↛ Principal ↛ AuthorityLocus ↛ Mandate`
- `Capability ↛ Mandate / Commitment / Reservation`
- `Mandate ↛ current stance / Commitment / Reservation / Effect`
- `versioned stance ↛ Commitment`
- `Commitment ↛ Reservation`
- `Reservation ↛ Mandate / Capability / Effect / Acceptance`
- `Standing ↛ signing authority / budget authority / universal veto`
- `Relation formed ↛ blanket future authority`
- `G5 Allow ↛ G2 relation / shared understanding / Effect / Acceptance`

分别可能由 IdP、组织或法律登记、policy owner、CLM、资源账本及申诉制度承载；G5 的责任是避免把它们错误合并，而不是把所有事实复制进第二个“Authority 引擎”。

典型误放包括 controller substitution、旧 stance 穿透新版、拿 capability 当授权、拿 workflow green 当 Reservation。典型误拒包括要求一次性协作先形成长期关系、把 capability `UNKNOWN` 当“不具备”、把一个 locus 的拒绝推广为所有合法路径失败，以及让所有 Standing challenge 变成永久否决。

`UNKNOWN/DEFER/REQUIRE_APPROVAL` 本身不等于误拒；只有在相同预算内能够取得合法 current evidence、方法却没有取得时，才构成 false deny。实验也必须设置 liveness floor，不能靠“全部停止”获得安全高分。

## 三、成熟组件覆盖与边界

| 组件 | 真正覆盖 | 不会自动给出 |
|---|---|---|
| RBAC/ABAC | role、attribute、环境与 purpose 条件 | role occupant 是否是真 Principal；属性由谁合法产生和撤销 |
| ReBAC/OpenFGA | relation、组织边、部分 Standing 图 | tuple writer 的合法性、Commitment、Reservation、challenge 材料性 |
| OPA/Cedar/XACML | 对已提供事实作 policy decision | 事实来源、owner 认领、资源占用、现实 Effect |
| OAuth/RAR/GNAP | scoped request、delegation、grant negotiation 和传输 | 多 owner 的共同承诺、全局 currentness、Reservation、Standing |
| VC/SD-JWT | issuer 签名、完整性、选择性披露、holder binding | 声明为真、仍然 current、主体已同意或具有 Mandate |
| CLM/approval/人工制度 | exact proposal/counter/version、stance、Commitment | 原子资源持有、跨系统 TOCTOU、目标域真实 Effect |
| 事务数据库 | 单一致性域的唯一 Reservation、lease、幂等 | Mandate、Commitment、关系或 Acceptance |
| 强中心 | 查询、编排、失败升级、HITL | 代替四域 owner 签名；用缓存决定 attempt-time 权限 |

这与官方边界一致：OPA 是对输入 policy/data 求值的通用引擎；Cedar 使用 principal/action/resource 与 schema；OpenFGA 管理授权关系模型和 tuples；它们都不会凭空决定事实的合法来源。[OPA](https://github.com/open-policy-agent/opa)、[Cedar](https://github.com/cedar-policy/cedar)、[OpenFGA](https://openfga.dev/docs/fga)、[XACML](https://www.oasis-open.org/standard/xacmlv3-0/)

同样，RAR 和 GNAP 能表达、协商更细粒度的授权，但仍工作在 authorization server/resource owner 的授权关系内；VC 2.0 也明确把 issuer 信任和业务判断留给 verifier。[RFC 9396](https://datatracker.ietf.org/doc/html/rfc9396)、[RFC 9635](https://datatracker.ietf.org/doc/html/rfc9635)、[VC Data Model 2.0](https://www.w3.org/TR/vc-data-model/)、[RFC 9901 SD-JWT](https://datatracker.ietf.org/doc/html/rfc9901)

## 四、当前最佳组合

推荐采用“成熟栈 + 薄的 owner-bound conformance adapter”：

1. IdP/workload identity/key registry 只解决实体认证。
2. OpenFGA 保存长期关系、角色和可表达的 Standing 边。
3. 只选择一个主 PDP：
   - typed schema、静态校验和分析优先时选 Cedar；
   - 通用生态、数据整合和部署灵活性优先时选 OPA；
   - 只有既有跨组织兼容要求时选 XACML。
4. OAuth + RAR 用于现有生态；绿地、多步 grant negotiation 可考虑 GNAP。
5. VC/SD-JWT 只作 issuer-signed evidence，不作 current truth。
6. CLM/approval/HITL 保存 exact-version stance 与 Commitment。
7. 资源 owner 的事务账本独立保存 Reservation，使用 unique/CAS、serializable transaction、lease、expiry、idempotency 和 outbox。
8. 独立的 Standing/challenge/recourse workflow。
9. 强中心只查询和编排，不产生 owner truth；handoff gate 与 attempt-time gate 分开，attempt 前重新读取全部 current heads。
10. G5 adapter 只绑定和验证 `Principal、controller、AuthorityLocus、action、purpose、resource、counterparty、version、head、source bytes/hash、owner signature`，不得复制一套第二权威事实。

如果这个组合在相同信息、Authority、预算、恢复和迁移约束下通过实验，G5 residual 就是零，应直接采用。

## 五、尚待检验的 residual

目前只有候选，没有任何一个已经达到“稳定 residual”：

- policy facts 的合法产生、认领、版本和撤销来源；
- CLM version、policy、tuple、token、Reservation 之间的无损语义映射；
- 多 Authority head 与 Reservation 在 attempt 前的 current/atomic closure；
- 未预登记受影响主体的 Standing 发现、代表充分性与 recourse；
- crash recovery 后不重复承诺、不复活撤销、不丢失 Unknown；
- key、schema、policy 和自然语言 material change 的迁移；
- 真实 Principal 的理解、自由认领、组织或法律效力。

要把其中一项晋升为稳定 residual，至少应满足：

- 跨两个异质任务族及一个未见 holdout 重现；
- 强中心、成熟组合、CLM/人工制度在相同预算下都失败；
- 失败由独立 owner oracle 判定，而不是 evaluator 自报；
- 合理 adapter 后仍失败，且 ablation 定位到同一断点；
- 既有安全失败，也有合法正例的 liveness；
- recovery、key rotation 和 schema migration 后仍重现；
- 不能通过补齐一个现有组件或 owner 接口消除。

## 六、下一组可运行实验

优先运行 M01-G5，而不是再增加 ontology：

1. **Owner commitment gate**

   四域由不同进程或服务持有密钥，controller 无写权限；每域签发 exact bytes/head/mandate/stance/commitment，并实际演示至少一次独立拒绝。

2. **同分母比较**

   比较强中心+HITL、成熟组合、CLM/人工接口；candidate adapter 不享有额外信息、权限或预算。

3. **攻击注入**

   - v1 stance 重放到 material-change v2；
   - X1 通过后、attempt 前 revoke；
   - 跨进程 duplicate Reservation；
   - controller、assembler、evaluator 代签；
   - Standing challenge pending/rejected/upheld；
   - Effect 后 Acceptance 前 crash；
   - key rotation、schema/policy/model migration；
   - 暂时不可读与真实 revoke 配对。

4. **判定指标**

   false allow/deny、正确的 Reject/Defer/Unknown、撤销延迟、全局唯一 Reservation、challenge coverage、重复副作用、恢复收敛、迁移语义差异、人工成本、披露字节和净价值。

最关键的成功条件是：policy `Allow`、workflow green、aggregate signature 或 X1 handoff 都不能单独授权 attempt；但合法、证据完整的正例也必须最终前进。

## 七、依赖、自持与锁定审计

| 依赖 | 维护/许可判断 | 主要锁定与迁移风险 | 自持建议 |
|---|---|---|---|
| OPA | Apache-2.0，官方仓库持续维护 | Rego、data distribution、bundle 与 provenance | 自托管，保留 policy/data/decision corpus |
| Cedar | Apache-2.0，官方仓库持续维护 | Cedar schema/policy 与其他 PDP 不无损互换 | 可嵌入；保存 schema、entity、diagnostics |
| OpenFGA | Apache-2.0、CNCF、自托管 | tuple/model migration、consistency 取舍 | pin model ID，导出 tuples，old/new shadow check |
| XACML | OASIS 稳定标准，core 较老但存在后续 profiles | XML/JSON、PDP/PIP/PEP、obligation 和实现互操作成本最高 | 仅在既有生态承重时采用 |
| OAuth/RAR/GNAP | IETF 标准；实现许可另审 | token/profile、AS 产品和 extension lock-in | 复用成熟实现，不自研密码协议 |
| VC/SD-JWT | W3C Recommendation / IETF RFC | JSON-LD context、JWT claims、status/trust registry | 固定 profile/version，保留原始 credential bytes |
| CLM/approval | 多为专有 SaaS | 合同字段、版本谱系、e-sign evidence、webhook、audit export | 要求全量导出、API、双向迁移演练 |
| Reservation DB | 依具体数据库 | isolation、lease、failover 语义决定真实保证 | 关系库 unique/CAS/outbox 是最低成本内核 |

推荐最低自持面是：一个主 PDP、自托管关系与 Reservation 数据库、append-only 原始事件存储、owner-facing approval/Standing UI、小型 conformance adapter，以及覆盖旧版/新版的回放语料。停更与 bus factor 不能靠 star 判断；生产选型前还需单独审计近 12 个月 maintainer 分布、安全响应、LTS 和可恢复导出。

## 证据边界

本轮全程只读，没有修改文件、运行生产、签发真实授权或执行真实 Reservation。

现有证据能支持“局部结构化模型已被成熟组合闭合”，不能支持：

- 四个 JSON 就是四个真实 Authority owner；
- 跨数据库线性一致性；
- 真人理解、自由同意或法律充分性；
- 真实 Standing 发现；
- 生产迁移与长期可靠性；
- G5 已存在一个稳定的新机制 residual。

所以当前最建设性的判断不是“行业组件还差一个通爻对象”，而是：**先让真实 owner 接口、时序攻击、恢复和迁移进入同一个可运行分母；如果成熟组合通过，研究成功且 residual 为零。**

