# G5 ChatGPT Pro 返回独立敌对审计

日期：2026-07-29  
审计对象：`G5-return.md`  
对照：同轮 `codex-cli-cohort-001/G5-final.md`、Wave 009 G2/G5 设计、实现、冻结结果与
`research/NOW.md`  
状态：`INDEPENDENT_ADVERSARIAL_AUDIT / NO_FORMAL_PROMOTION`

## 总裁决

Pro 返回最有价值的部分，是拒绝再造一个通用 Authority 协议，并把 Identity、Mandate、
Permission、Commitment、Reservation、Standing、Challenge、Acceptance 等非蕴含关系拆开。
其主流技术的原生边界、标准状态和大部分许可判断也基本准确。

但它尚未给出一个已经闭合现实 G5 的成熟组合。报告把三种不同强度的内容放在了一起：

1. 已由官方资料或本地合成实验支持的组件事实；
2. 合理但尚未跨真实 owner、故障域和产品实现运行的工程设计；
3. 被写成“最强答案”“最稳定 residual”或“强中心应当获胜”的比较性结论。

第三类目前过强。最关键的五个收窄是：

- typed evidence 与 exact object/version 是重要的防误绑手段，但首先是建模与
  conformance 纪律，不是已证明的未解机制；
- `owner-controlled authoritative registry` 把最困难的 current truth 生产、认领、
  非等价分叉、撤销和可用性藏进了前提，不能作为免费 oracle；
- OPA、Cedar、OpenFGA、XACML 的原生结果不能无损、通用地映射为
  `ALLOW / REJECT / UNKNOWN / DEFER`；
- commit-time read set 和 fencing 只能在各自明确的一致性域和真实 enforcement point
  内提供保证，串行重读多个独立 head 不会自动形成跨 Authority 原子快照；
- “同一中心拥有所有技术读写权限”不等于“一个 Principal 真实统一了全部 Authority”。

因此本审计对 Pro 返回的整体判断是：

```text
PLAUSIBLE_AS_MATURE_COMPOSITION_DESIGN
OVERSTRONG_AS_REAL_WORLD_CLOSURE
NO_STABLE_G5_RESIDUAL_ESTABLISHED
NO_NEW_PROTOCOL_JUSTIFIED
```

这不是否定成熟组合。相反，若后续真实 owner 试验表明强中心或成熟组合在同分母下完整解决，
应直接采用，residual 可以为零。

## 本地证据复核

### 已复现

- 重新运行
  `experiments/wave-009-g2-g5-crossed-square/tests/test_wave009_crossed_square.py`：
  `28/28 PASS`。
- 冻结结果文件
  `experiments/wave-009-g2-g5-crossed-square/outputs/results.json` 的 SHA-256 仍为
  `7b618c626a7f4d466eeeab295d531a5257776f2f45d1e363ffdbab0587e6d28a`。
- 当前结果确实报告 B0、B5 的 G2/G5/integration 均为 `24/24`，且 11 项 residual
  matrix 全部通过。

### 不能外推

Wave 009 README 已明确限定：

- 24 个 world 是冻结合成 world，不是真实 T3/T4；
- reservation 原子性只来自单进程 Python lock；
- B0/B1/B5 是 `DISTINCT_PATHS_SAME_AUTHORING_STREAM`；
- B3A/B3B 只是 `OpenFGA + Cedar/OPA` 的形状；
- B5 是本地 Python 中的 policy/commitment/ledger/standing 组合，不是实际 OPA、Cedar、
  OpenFGA、CLM 和数据库产品集成；
- 未证明真实 Principal、自然语言、跨故障域线性一致性、生产迁移或长期漂移。

代码也与该限定一致：`baselines.py:942-952` 只把本地 `policy_authority` 包装路径标成
`OPENFGA/CEDAR` 或 `OPENFGA/OPA`；`baselines.py:960-971` 的 B5 只是相同代码库内的
组件标签和布尔组合。

所以本地证据支持：

> 在已预结构化、truth broker 可直接签发正确事件、受信 parent、单进程原子账本的有限模型
> 中，现成能力形状足以构成正确路径。

它不支持：

> 已有产品组合已经取得四个真实 Authority owner 的 current truth，并在现实跨域失败、
> 撤销、恢复与迁移下闭合 G5。

## 逐项裁决

### G5-A01 — 各类证据不存在自动蕴含

**裁决：VERIFIED**

Pro 在 `G5-return.md:146-165` 区分 Identity、Authority、Mandate、Permission、stance、
Reservation、Commitment、Standing、Challenge、Acceptance、ACK 和 workflow green。这与
Wave 009 的非蕴含门一致，也与 VC、policy engine、e-sign 和事务数据库的官方职责边界一致。

**最强反例攻击：** 即使字段被严格 typed、签名有效，issuer 仍可能没有对应 Authority，
或 owner 签的是不完整投影。类型与签名只证明输入符合某合同，不证明合同覆盖了现实中的
material fact。

**最小修订门：** 把“没有 typed rule 就不能升级”收窄成实现不变量：
`adapter 不得在没有显式、owner-approved mapping rule 时自动升级`；不要把它写成所有现实
制度都必须采用同一 Evidence schema 的理论定律。

**下一实验改变：** 保留当前非蕴含正负例，但增加“全部字段合法、签名合法、issuer 无对应
Authority”的 holdout，以及“schema 完整但遗漏 sidecar/material dependency”的正交攻击。

### G5-A02 — exact object/version/digest 是跨层必要绑定

**裁决：PLAUSIBLE**

对合同、artifact、BOM、policy bundle 等可冻结对象，exact binding 是强而成熟的安全纪律。
Wave 009 也已证明 exact bytes/context 能阻止旧 section、跨 world 和 event transplant。

**最强反例：** 一个部署可以有固定 artifact digest，却在执行前改变 feature flag、secret
version、数据库状态或外部依赖；一个合同 PDF digest 固定，也可能没有覆盖引用的 tariff、
附件或后续生效的监管条款。单个 object/version 不是完整 causal closure。反过来，两个序列化
字节不同的对象也可能在领域语义上等价。

**最小修订门：** 将 `exact object` 改为
`owner-approved material operation closure`：列出直接对象、规范化规则、所有 material
引用、可变外部依赖、允许变动范围和重新授权条件。digest 只绑定已声明闭包。

**下一实验改变：** 加入两组 paired worlds：

1. 同 digest、外部 material dependency 不同；
2. 不同 bytes、经 owner-approved canonicalization 后语义等价。

若方案仍只按单一 digest 判定，应分别暴露 false allow 和 false deny。

### G5-A03 — “成熟组合已能闭合大部分现实任务”

**裁决：OVERSTRONG**

`G5-return.md:29-30` 没有现实运行分母支持“大部分”。三个任务都是实验设计；Wave 009
明确是 local synthetic，B5 也不是独立产品组合。

**最强反例：** M01 即使有四份 authority JSON，也没有四个独立 owner 进程、独立拒绝权、
真实密钥域、current-head 服务或现实后果。用这些 JSON 通过 B5 不能推断跨企业采购、医疗
同意或租户发布已闭合。

**最小修订门：** 改为：

> 成熟组件分别覆盖了大部分所需局部能力；它们能否在真实 owner 和相同成本约束下端到端
> 闭合，尚未运行。

**下一实验改变：** 至少在一个低风险、可撤销真实任务中接入真实 owner-facing approve /
reject / revoke 接口、真实事务资源和真实 target readback；没有该结果前不使用“现实任务
已闭合”。

### G5-A04 — 四值 `ALLOW / REJECT / UNKNOWN / DEFER` 可跨层保真

**裁决：OVERSTRONG**

四值业务状态本身有用，但不是四类产品共享的原生语义：

- OPA 可返回任意结构，但状态含义完全由本地 Rego 与调用方定义；
- Cedar 最终只返回 Allow/Deny，并附 determining policies 与 evaluation errors；
  其 skip-on-error 甚至允许某条 policy 报错而另一条 permit 仍使总结果为 Allow；
- OpenFGA Check 返回 `allowed=true/false`；未定义 relation 可返回 `400`，缓存陈旧和 transport
  failure 也不是 owner Reject；
- XACML 有 Permit、Deny、NotApplicable、Indeterminate，但 NotApplicable 是“当前目标没有
  适用 policy”，Indeterminate 是 evaluation error family，并不天然等于业务 Unknown 或
  Defer。

Pro 自己在 `G5-return.md:335-343` 承认 XACML 不能直接映射，却仍在
`G5-return.md:52-65, 167-173, 672` 将四值写成可跨层保真的最低共同结果，结论强于证据。

**最强反例：** Cedar 中一条 material policy 因缺属性报错，但另一条 permit 成立，native
decision 为 Allow；同一输入在 XACML 中可能为 Indeterminate，在 OpenFGA 中可能是 false
或 400。若 wrapper 只看最终 decision，会误放；若把所有异常都映射 Unknown，则会把明确
Deny/forbid 或不可恢复 schema 错误误标成可恢复未知。

**最小修订门：** 不要求 native outcome 直接映射。统一层必须保留：

```text
native_engine
native_outcome
native_error/status
policy/model version
input completeness
source freshness
negative authority fact
resolver/event that can change state
adapter mapping version
```

业务四值只能由 task-specific、版本化、owner-approved mapping 派生；无法证明映射时保持
`UNMAPPED_NATIVE_OUTCOME`，不得自动变成 Allow。

**下一实验改变：** 用真实引擎运行同一 corpus：

- OPA undefined、built-in error、stale bundle；
- Cedar no-permit、forbid、skip-on-error + independent permit；
- OpenFGA false、undefined relation 400、stale cache、`HIGHER_CONSISTENCY`；
- XACML Permit/Deny/NotApplicable/各类 Indeterminate、obligation failure。

评分 raw outcome 保真和业务映射正确性，禁止 evaluator 直接提供四值 label。

### G5-A05 — owner-controlled authoritative registry 提供 current truth

**裁决：UNRESOLVED**

`G5-return.md:632-650` 的字段列表合理，但“它是相应 owner 的 authoritative readback”正是
待解决条件，不是数据库、VC、目录或 CLM 自动提供的能力。

**最强反例：** 同一 owner 或其被攻陷 writer 对两个 verifier 分别签发
`head=18 SUPPORT` 与 `head=19 REVOKED`；两者都签名有效。另一个反例是撤销在法律上于
`t_effective` 生效，但 registry 在 `t_publish > t_effective` 才可读。单一 `current_head`
字段不能证明非等价分叉、发布完整性、effective time 或调用时的真正 currentness。

**最小修订门：** 每个 registry profile 至少要冻结：

- 谁有写权，写权为何等于或受托于规范 Authority；
- monotonicity、fork/equivocation 检测和历史保留；
- `issued_at / effective_at / observed_at / expires_at`；
- freshness SLA 和不可读时的决策；
- 是否需要 append-only witness、独立审计锚或 quorum；
- owner key compromise 和恢复规则；
- readback 被哪个现实执行方接受为权威。

**下一实验改变：** 四个 owner 由独立进程与密钥域运行，controller 只读；注入 forked head、
delayed publication、backdated revocation、owner outage、key compromise 和合法 supersede。
评测不得把 broker 的隐藏真值 API交给方法。

### G5-A06 — commit-time read set 可关闭跨 Authority TOCTOU

**裁决：OVERSTRONG**

`G5-return.md:755-792` 是合理 checklist，但顺序重读多个外部 head 不会形成同一时刻的全局
快照。它能发现一部分已观察变化，不能证明所有 Authority 在签名和执行时同时稳定。

**最强反例：**

```text
read A=head10
read B=head20
re-read A=head10
B changes to head21
obtain final signature
A changes to head11
execute
```

所有既有读回都曾正确，read set 仍未代表单一 commit instant。若使用 2PC，则独立 owner
需要进入 prepare/hold，并承担锁持有、阻塞和恢复成本；若使用 saga，则是补偿而非原子撤销。
Gray 与 Lamport 的原始 transaction-commit 研究也明确区分会在 coordinator failure 下阻塞
的经典 2PC 与更高成本的 fault-tolerant commit。

**最小修订门：** 把保证拆成：

1. 单 Authority consistency domain 内的 atomic snapshot/CAS；
2. 跨 Authority 的 bounded-validity evidence；
3. 无共同事务管理器时的 prepare/confirm、abort、expiry 或 compensation；
4. 执行点的最后 readback；
5. 明确承认无法获得 simultaneous snapshot 时返回 Defer/Unknown。

**下一实验改变：** 用独立 owner 服务在每一个“最后重读”后注入 revoke；测量 false allow、
锁持有时间、abort/retry、不可用窗口和人工补偿，而不只测 stale head 被预先放入事件流。

### G5-A07 — fencing token 防止过期 executor

**裁决：PLAUSIBLE**

fencing 是成熟的并发安全模式，但保证来自“真实 resource enforcer 拒绝旧 epoch”，不是
controller 携带了一个 token。Chubby 原始论文使用 epoch/sequence 让服务拒绝旧客户端请求，
说明验证点和单调序列才是关键。

**最强反例：** reservation ledger 发出 token 42，lease 过期后发出 43；旧 executor 带 42
直接调用不检查 token 的设备、供应商门户或人工流程，仍然产生 Effect。token 存在但没有
enforcement coverage。类似地，idempotency key 只有在 key、exact request 和既有结果被
原子保存，并且保留期覆盖所有重试时才防重；key 过期、下游另行产生副作用或同 key 接受变更
bytes，仍可重复执行。

**最小修订门：** 每个 fenced resource 必须声明 token authority、严格单调性、持久化方式、
所有 side-effect endpoint 的比较规则、failover 行为和不支持 fencing 的补偿路径。
idempotency 还要声明 key scope、request equality、retention、conflict 和结果 replay 规则。

**下一实验改变：** 在 lease expiry 后让旧 executor 真实抵达 target adapter；分别测试
target 正确拒绝、忽略 token、重启丢失最高 epoch、跨 region 顺序倒置。指标是 stale Effect，
不是 ledger 是否生成了 conflict。

### G5-A08 — challenge/standing case object 能保存异议

**裁决：UNRESOLVED**

`G5-return.md:722-739, 1173-1189` 给出的 case 字段和 coverage 维度有建设性，但它只保存已知
challenge；没有解决受影响主体发现、standing 冲突、辖区变化或挑战权在执行后才被承认。

**最强反例：** 一个未登记的下游数据主体在执行后被裁判认定具有 standing；执行前 registry
和 aggregate receipt 中都没有该主体。完整 case schema 无法发现它。另一个反例是同一
challenge 在合同制度中 non-suspensive、在监管制度中 suspensive，单一 effect 字段无法
自行决定优先级。

**最小修订门：** 分开记录：

- candidate affected parties discovery；
- asserted standing；
- provisional standing；
- authoritative adjudicated standing；
- jurisdiction/rule version；
- challenge 对 reserve、execute、settle、accept 的分别效果；
- late-discovered party 的 reopen/compensation。

**下一实验改变：** 增加未预登记 stakeholder、冲突辖区、late standing、恶意阻塞 challenge
和被驳回 challenge。评分既要覆盖合法 objection，也要有 liveness floor，不能让所有
challenge 永久停机。

### G5-A09 — migration loss manifest 与 differential testing 解决语义迁移

**裁决：PLAUSIBLE**

这是强控制措施，但只能证明“已知字段和已运行 corpus 未观察到差异”，不能证明两个逻辑
无损等价。

**最强反例：** 迁移语料没有触发 XACML obligation failure 或 Cedar skip-on-error 分支，
所有 differential cases 均一致；生产中的第一个该分支却产生不同结果。另一类是非单射映射：
两个源状态被压成一个目标状态，round trip 无法恢复，loss manifest 也只能列出已识别的损失。

**最小修订门：** 把结论限定为 witnessed equivalence，并要求：

- source/target native outcome corpus；
- absence、negative fact、error、combining、obligation、time 和 delegation semantics；
- source bytes/provenance；
- 未映射字段 fail closed；
- policy owner 对 mapping version 的认领；
- 一旦发现新差异自动降级旧 mapping。

**下一实验改变：** 选择两种真实异构表示做双向迁移和 shadow decision，不用统一 JSON
simulator。必须加入未见 holdout、metamorphic cases、故障和版本升级；报告 corpus 外仍为
Unknown，而不是“可证明保存”。

### G5-A10 — 强中心在真实统一 Authority 下应成为首选

**裁决：PLAUSIBLE**

作为候选基线是正确的；作为“应当获胜、最低延迟/维护成本”的实证结论尚未运行。Wave 009
只验证 B0 与 B5 在同一合成矩阵中正确率相同，没有真实成本、可用性或长期维护数据。

**最强反例：** 一个集团对平台数据库有统一管理员权限，但客户仍保留不可代行的变更批准；
管理员可写 `approved=true`，却没有规范 Authority。另一个反例是同一法人内部的付款、
安全、审计分权由制度强制，单一 legal entity 并不等于单一可合并 Authority。

**最小修订门：** `unified Authority` 必须同时满足：

1. 同一 Principal 真实拥有或获合法可转委托的每一项 required Authority；
2. 没有仍相关的外部 non-delegable right、acceptance 或 standing；
3. 中心写入被所有现实 effect/settlement 域接受；
4. separation-of-duties、监管和审计要求允许集中；
5. 不是仅有同一账号、管理员权限、数据副本或 controller visibility。

**下一实验改变：** 建立只差一个变量的 paired worlds：

- U：一个 Principal 真实拥有全部 required Authority；
- P：基础设施、账号和读写权限完全相同，但一个 non-delegable Authority 属于外部 owner。

正确强中心应在 U 内直接闭合，在 P 内查询/等待 owner；若两者同判，说明把“同权限中心”
误当成“统一 Authority”。

### G5-A11 — 强中心可在一个 ACID transaction 中合并全部记录

**裁决：OVERSTRONG**

只有当所有权威状态和 side effect 都在同一事务资源管理器内，`G5-return.md:525-537` 才成立。
调用 CLM、外部设备、人工签署、OAuth AS 或客户系统时，一个本地 ACID transaction 只能原子
记录 intent/outbox，不能把外部 Effect 一并纳入。

**最强反例：** 中心事务提交了 reservation、commitment record 和 outbox，外部设备已经
执行但回执丢失；重试可能重复 Effect，不重试可能漏记 Effect。数据库内部完全一致，现实
仍不确定。

**最小修订门：** 将“一个 ACID transaction 完成”改成：

> 对中心拥有的记录可在一个事务中提交；外部 side effect 需要 idempotency、outbox/inbox、
> target readback、reconciliation 和必要 compensation。

**下一实验改变：** 在事务提交、消息发送、目标执行、回执和 readback 之间逐点 crash，
检查重复 Effect、半完成、恢复收敛与最终 Acceptance。

### G5-A12 — 本地 Wave 009 已证明 B0/B5 在有限模型内闭合

**裁决：VERIFIED**

28 个测试已独立重跑通过，冻结 hash 匹配；README 和结果文件对范围的表述诚实。

**最强反例攻击：** 攻击不是当前测试失败，而是将同一 authoring stream 和 truth broker
预结构化输入误称为三种独立成熟产品或真实 Authority。README 已明确禁止这种外推。

**最小修订门：** Pro 应引用最窄状态
`POSITIVE_LOCAL_SYNTHETIC_EXISTING_COMPOSITION_SCOPED`，并明确 B5 是组件形状，不是产品
验收。

**下一实验改变：** 用独立实现者和真实产品替换至少一个 policy/relationship/transaction
组件；truth owner 不与 adapter/evaluator 同 authoring stream。

### G5-A13 — 当前没有证据要求新通用 Authority 协议

**裁决：VERIFIED**

现有资料只支持局部模型中的成熟组合正例和若干待证跨合同断点；没有稳定、跨任务、跨实现、
同分母失败的 residual。负面结论“尚未证明需要新协议”与证据相称。

**最强反例攻击：** 未来真实 owner 试验可能复现无共同事务管理器、privacy/freshness 或
semantic migration 的稳定缺口；这会重开研究，但不能被当前候选列表提前算作已发现。

**最小修订门：** 保持“当前未证明”，不要升级成“理论上永远不需要”。

**下一实验改变：** 严格按同预算比较 strong center、成熟组合、人工/CLM、general model；
只有它们都在相同断点失败且 adapter 无法修补，才提出新机制。

### G5-A14 — exact binding/current-head/challenge/migration 是“最稳定 residual”

**裁决：UNRESOLVED**

`G5-return.md:52-65, 1432, 1553-1611` 多处称这些为最稳定或可能稳定 residual，但报告没有
在真实产品、真实 owner 或两种异质迁移中运行。

**最强反例：** 一个成熟强中心在真实统一 Authority 场景中用单一版本库、事务和人工制度
完整解决，所有候选 residual 为零。另一个可能结果是失败来自缺失 owner API 或错误配置，
而不是跨层协议缺口。

**最小修订门：** 全部改称 `candidate residual / experiment target`，直到满足报告自己在
`G5-return.md:1615-1631` 提出的重复、同分母、独立产品、counterfactual 和成本门。

**下一实验改变：** 不先实现 canonical IR。先运行真实 native outcomes 和 owner process；
若 adapter 已闭合，IR 不应因预注册而获得机制身份。

### G5-A15 — 相对优劣与成本判断

**裁决：UNRESOLVED**

OPA“最适合编排”、Cedar“通常更优”、OpenFGA“最强关系层”、XACML“复杂度最高”、
CLM/e-sign“最强 Commitment 层”、强中心“最低成本”等都是合理经验假设，但没有统一任务、
团队能力、SLA、迁移与恢复分母。

**最强反例：** 已有 XACML 团队可能比新引入 Cedar + wrapper 成本更低；领域原生订单或
医疗同意系统可能比通用 CLM 更能表达 commitment；一个中心的 p99 会被最慢人工复核主导，
并不自动低延迟。

**最小修订门：** 将所有“最强/通常优于/应获胜”改成方向性假设，并声明适用环境。

**下一实验改变：** 同时测量：

- p50/p95/p99 与最大等待；
- 外部 read 次数和可用性乘积；
- human minutes、队列和 disagreement；
- reservation hold time、abort/retry、compensation；
- disclosure bytes；
- policy/schema/adapter 维护工时；
- upgrade、restore、export/import drill；
- false allow/deny 与 liveness。

没有这些数据，不报告全生命周期赢家。

## 外部技术事实核验

以下只使用官方文档、官方仓库或原始论文。

| Pro 陈述 | 裁决 | 核验与限制 |
|---|---|---|
| OPA 是通用策略引擎；external data/policy 通常是 cache/replica；bundle 是 eventual consistency；decision log 含 input、policy、bundle metadata | VERIFIED | [OPA External Data](https://www.openpolicyagent.org/docs/external-data)、[Bundles](https://www.openpolicyagent.org/docs/management-bundles)、[Decision Logs](https://www.openpolicyagent.org/docs/management-decision-logs) 直接支持。它不支持把 OPA 当 owner current truth。 |
| Cedar 请求为 principal/action/resource/context，最终 Allow/Deny，forbid-overrides-permit、default deny、diagnostics、schema validation | VERIFIED | [Cedar Authorization](https://docs.cedarpolicy.com/auth/authorization.html) 和 [Validation](https://docs.cedarpolicy.com/policies/validation.html) 支持。重要遗漏是 skip-on-error：错误 policy 被跳过，不能只把 diagnostics 理解为“最终 Deny”。 |
| OpenFGA model 不可变、应 pin model ID、Check 本质为关系 yes/no | VERIFIED | [Immutable Models](https://openfga.dev/docs/getting-started/immutable-models)、[Perform a Check](https://openfga.dev/docs/getting-started/perform-check) 支持。undefined relation 返回 400，不是 false。 |
| OpenFGA `HIGHER_CONSISTENCY` 可作为 current truth | OVERSTRONG | [Consistency Modes](https://openfga.dev/docs/interacting/consistency) 只保证跳过 OpenFGA cache、直读数据库；它没有生成跨 CLM、Mandate registry、reservation 的原子 currentness，也不是 Zanzibar-style zookie。 |
| XACML 3.0 有 Permit/Deny/NotApplicable/Indeterminate、obligations/advice | VERIFIED | [XACML 3.0 Core](https://docs.oasis-open.org/xacml/3.0/xacml-3.0-core-spec-cos01-en.html) 直接支持；四个 native outcome 不等于四个 G5 业务状态。 |
| 2026-02 发布 ACAL 1.0 与 JACAL CSD01，仍是 draft | VERIFIED | [ACAL CSD01](https://docs.oasis-open.org/xacml/acal/acal/core/v1.0/csd01/acal-core-v1.0-csd01.html) 与 [JACAL CSD01](https://docs.oasis-open.org/xacml/acal/jacal/core/v1.0/csd01/acal-core-json-v1.0-csd01.html) 日期均为 2026-02-18。Pro 未提同批 XACML 4.0 XML representation CSD01，但不改变其核心判断。 |
| GNAP 已有 Standards Track RFC | VERIFIED | [RFC 9635](https://www.rfc-editor.org/rfc/rfc9635.html) 于 2024-10 发布，确实处理软件 delegated authorization 和 grant negotiation。 |
| GNAP 生态成熟度低于 OAuth、实现选择较少 | UNRESOLVED | RFC 不提供采用率、实现数或维护健康度；需要单独的实现/互操作/生产采用审计。 |
| VC Data Model 2.0、Bitstring Status List 1.0 在 2025 成为 Recommendation | VERIFIED | [VC Data Model 2.0](https://www.w3.org/TR/vc-data-model/) 与 [Bitstring Status List](https://www.w3.org/TR/vc-bitstring-status-list/) 均为 2025-05-15 Recommendation。VC 规范还明确说 cryptographic verifiability 不代表 claim 为真，业务依赖由 verifier policy 决定。 |
| SD-JWT 是 RFC 9901；SD-JWT VC 截至 2026-07 是 draft-17 | VERIFIED | [RFC 9901](https://www.rfc-editor.org/rfc/rfc9901.html) 于 2025-11 成为 Standards Track；[SD-JWT VC Datatracker](https://datatracker.ietf.org/doc/draft-ietf-oauth-sd-jwt-vc/) 显示 active draft-17、2026-07-06 revision。 |
| embedded e-sign audit 必须结合应用认证日志 | VERIFIED | Adobe 官方 [Embedded Signing Identity and Authentication](https://helpx.adobe.com/sign/developer/signer-identity-in-workflows.html) 明确说明 signing URL 由集成应用交给 signer、应用负责自己的认证，audit trail 与应用日志任一单独都不完整。 |
| PostgreSQL range exclusion 可阻止范围重叠；Serializable 需要处理 serialization failure | VERIFIED | [Range Types](https://www.postgresql.org/docs/current/rangetypes.html) 与 [Transaction Isolation](https://www.postgresql.org/docs/current/transaction-iso.html) 支持。它只覆盖数据库 consistency domain。 |
| OPA、Cedar、OpenFGA 为 Apache-2.0；OpenFGA 可自部署并用 PostgreSQL/MySQL/SQLite；PostgreSQL 为 PostgreSQL License | VERIFIED | [OPA repo](https://github.com/open-policy-agent/opa)、[Cedar repo](https://github.com/cedar-policy/cedar)、[OpenFGA repo](https://github.com/openfga/openfga)、[OpenFGA configuration](https://openfga.dev/docs/getting-started/setup-openfga/configure-openfga)、[PostgreSQL License](https://www.postgresql.org/about/licence/) 支持。OpenFGA 截至当前是 CNCF Incubating，不应模糊成 Graduated。 |
| CLM/e-sign 锁定高、签署 PDF 可导出但完整 workflow 常不可无损迁移 | PLAUSIBLE | 风险方向合理，但 Pro 没有对具体供应商、套餐、导出 API、保留字段和 round-trip 做同分母测试；不能作为整个类别的已验证等级。 |
| DocuSign CLM API 支持“文档下载和版本管理” | UNRESOLVED | 本审计未从 Pro 保留的来源定位到足以支持该精确组合陈述的官方页面；不影响主论证，但应补精确 API/version 链接或删除。 |
| NIST 材料要求 recourse、appeal、override 与 adjudication 记录 | VERIFIED | [NIST AI RMF Playbook](https://airc.nist.gov/AI_RMF_Knowledge_Base/Playbook) 支持这些治理实践；它不证明所有 G5 领域的唯一 Authority 必然是人工制度，也不规定 Pro 的 challenge schema。 |

## 对最强成熟基线的最小修订

Pro 的 MCB-G5 不应被丢弃，但应从“端到端答案”改为“待运行组合假设”：

```text
MCB-G5-v2

1. 原生 truth owners
   - 每个 Authority fact 由独立 owner process 签发
   - controller 只读、不可代签、不可改 head
   - owner 可真实 reject/revoke/outage/equivocate

2. material operation closure
   - 不只绑定一个 object digest
   - 冻结 canonicalization、sidecars、external dependencies、materiality rule

3. native-outcome preservation
   - 保存 OPA/Cedar/OpenFGA/XACML 原生 outcome/error/version/freshness
   - task-specific mapping 才派生业务四值

4. consistency domains
   - 单域 transaction 与跨域 coordination 分开声明
   - 没有 simultaneous snapshot 时不宣称 atomic currentness

5. enforceable fence
   - target side-effect endpoint 必须验证 monotonic token
   - 不支持 fencing 的目标进入 compensation/reconciliation 分支

6. Standing lifecycle
   - affected-party discovery、asserted/adjudicated standing、jurisdiction、
     late challenge 与 liveness 分开

7. migration witnessed-equivalence
   - 只对运行 corpus 声明一致
   - source owner 认领 mapping，未知分支保持 Unknown

8. real acceptance/readback
   - execution receipt、target Effect、Adoption、Acceptance、Settlement 分开
```

## 下一实验必须改变什么

下一轮不应先实现新的 IR 或协议，而应把 M01/X1 改造成五个能真正区分解释的试验。

### E1 — Unified Authority / Same-Permission Center crossed pair

唯一差异是 Authority 所有权，不是技术权限：

- U：中心 Principal 真实拥有全部 required Authority；
- P：完全相同的账号、API、数据库权限，但一个 non-delegable right 属于外部 owner。

比较 strong center、成熟组合、CLM/HITL。U 中强中心胜出是正结果；P 中中心必须查询外部 owner。

### E2 — Native four-outcome translation

实际启动一个 OPA、Cedar、OpenFGA 和 XACML 实现或权威参考 evaluator，冻结原生输入和输出，
运行 A04 的错误、缺失、stale、NotApplicable、Indeterminate 和 forbid corpus。wrapper
不得预读 oracle 四值。

### E3 — Cross-owner time race

四个 owner 服务独立签发并可拒绝。每个 read、re-read、sign、reserve 和 execute 边界后都
可发生 revoke/outage/fork。比较：

- 无共同事务；
- bounded lease + confirm；
- 2PC-like hold；
- saga/compensation；
- 真实统一中心。

同时测安全、liveness、阻塞、人工和恢复成本。

### E4 — Fence-to-Effect

不是检查 ledger conflict，而是让旧 executor 到达 target。target 分别正确检查、忽略、
重启丢失或跨 region 乱序处理 token，最终由 target readback 判定是否产生 stale Effect。

### E5 — Migration and Standing holdout

迁移在两个真实异构语义间运行；保留一组 evaluator 不见的 holdout。再加入未预登记受影响
主体、late standing 和冲突 jurisdiction。只有 mapping、challenge 和 reopen 都经 owner/
adjudicator 认领，才算成功。

## 停止线

以下任一结果都应被视为研究成功，而不是失败：

- strong center 在 U 世界以更低净成本完整闭合；
- 成熟组合在 P 世界完整闭合，B6 增量为零；
- 人工/CLM 制度在低频高后果任务中成本最低；
- 某一候选 residual 被证明只是缺失 owner API、配置或事务约束；
- 四值统一层的成本高于保留各产品原生结果与一个薄 task adapter。

只有同一断点在至少两个异质任务、一个未见 holdout、两个独立实现中复现，并且强中心、成熟
组合、人工制度和合理 adapter 在相同信息、Authority、预算与恢复条件下都失败，才有资格
把该断点提升为稳定 G5 residual。

本审计不改变 `research/NOW.md`、`PROGRAM.md`、Problem、LineContract、MechanismProfile 或
任何正式研究状态。
