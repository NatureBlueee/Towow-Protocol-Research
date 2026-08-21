# C：G5 Authority conformance 敌对研究

状态：`INTERNAL ADVERSARIAL DESIGN / CORPUS DRAFT / NOT RUN`

本文件只攻击 MCB-G5-v2 的伪成功路径，不宣告 canonical IR、新协议或产品优劣。机器语料见
[`adversarial-corpus.json`](./adversarial-corpus.json)。

## 结论

当前最强反例不是某个 PDP 返回错误，而是三种被混为一谈的“中心”：

1. **SC-U：真实统一 Authority。** 一个 Principal 确实拥有或可合法承接所有 required
   Authority，且不存在外部不可代行权、强制分权或外部 Effect。强中心在这里完整闭合并以更低
   成本胜出，是应保留的正结果。
2. **SC-P：相同技术权限、外部 non-delegable right。** 中心拥有与 SC-U 完全相同的账号、
   API、数据库写权和可见性，但 Acceptance、患者同意、客户批准或另一 owner 的 Commitment
   仍不可代行。中心能够写 `approved=true`，不等于它有权产生这个事实。
3. **SC-E：单域事务、外部 Effect。** 中心能在一个 ACID transaction 内写 policy、
   reservation、commitment record 和 outbox，但设备、供应商门户、外部机构或人类流程才产生
   Effect。本地原子性不等于现实 Effect 原子性。

只要一个实现不能区分这三类，它的“强中心通过”就没有解释力。SC-P 是最锐利的 crossed
pair：技术权限完全不变，唯一改变的是 Authority owner。若方法两侧同判 Allow，它测到的是
管理员能力，不是 Authority conformance。

## 应阻断的六类伪成功

### 1. 免费 authoritative registry

“owner-controlled registry”不能作为无成本、永远 current 的 oracle。它至少包含写权的规范
来源、单调性、fork/equivocation、`issued/effective/published/observed/expires` 时间、
freshness SLA、outage 语义、key compromise 与恢复规则。

语料把以下情况分开：

- fork：两个签名都有效，但不同 verifier 看见不同 head；
- delayed publication：撤销已经生效，却尚未对 verifier 可读；
- backdated revocation：不能用一条通用规则把全部历史签名追溯作废；
- outage：当前性不可得是 `UNKNOWN`，不是 owner `REJECT`；
- key compromise：签名密码学有效也不能自动成为 live permission。

因此，比较各 arm 时必须把 owner read、SLA、故障和维护成本计入同一预算。给某 arm 一个
“current registry”而不计 truth 生产和恢复，相当于泄漏 oracle。

### 2. 顺序重读冒充跨 Authority 原子快照

在 `read / re-read / sign / reserve / execute` 每个边界后都可以撤销、离线或分叉。
顺序重读多个独立 head 只证明“每个值曾在某个观察时刻成立”，不证明存在一个共同 commit
instant。签名也不冻结可撤销意志，Reservation 更不蕴含 Mandate。

语料要求实现逐边界接受 race：

- read 后 revoke；
- 最后 re-read 后另一 owner 改 head；
- sign 后 revoke；
- reserve 后 mandate revoke；
- execute 后、receipt 前 crash。

成熟的合法解可以是 owner hold/prepare-confirm、bounded lease、abort、Saga、人工补偿，或在
无法获得足够稳定性时 `DEFER/UNKNOWN`。要求不是伪造 ACID，而是准确声明 consistency
domain、阻塞、恢复和残余。

### 3. exact digest 冒充 material operation closure

单一 digest 既会 false allow，也会 false deny：

- 相同 artifact/PDF bytes 可能引用变化后的 tariff、feature flag、secret、数据库状态或
  监管规则；
- main object 不含 `no-training` sidecar 时，主 digest 相同仍可能越权；
- 不同序列化 bytes 经 owner-approved canonicalization 可能完全等义；
- 未经领域批准的 canonicalization 也可能把单位、精度或 absence semantics 压平。

所以对象闭包必须显式冻结 canonicalization、sidecars、external dependencies、materiality
rule、允许变动范围与重新授权条件。语料同时含 material drift 和 nonmaterial drift；只要
“任何变化都拒绝”，也会因 liveness false deny 失败。

### 4. ledger token 冒充 target fence

fencing 的保证来自目标端拒绝旧 epoch，不来自 ledger 发出了一个整数。必须让旧 executor
真正抵达 target，并区分：

- target 持久化最高 token 并拒绝旧请求；
- target 忽略 token；
- target restart 后丢失最高 token；
- region A 已接受 43、region B 因复制延迟仍接受 42。

评分真值是 target authoritative readback 中是否产生 stale/duplicate Effect。只检查
reservation conflict 或 token 生成会放过最危险的现实副作用。

### 5. Standing registry 冒充完整受影响者集合

完整 case schema 只能保存已发现的 challenge，不能证明所有 affected party 已被发现。
语料要求：

- 未预登记 stakeholder 执行后首次出现；
- late standing 经裁决成立；
- 合同制度 `non-suspensive` 与监管制度 `suspensive` 冲突；
- 恶意、重复、无依据 challenge 被按时驳回；
- 合法 pending challenge 有 resolver、deadline 与分阶段 effect。

只求安全而永久冻结全部行动不是成功。Standing 评测必须同时有 objection coverage 和
liveness floor，并把 reserve/execute/settle/accept 的 effect 分开。

### 6. 迁移绿灯冒充语义等价

不同 policy、relation、credential 和 CLM 表示之间最多先声明
`WITNESSED_EQUIVALENCE(corpus, versions, mapping)`。必须保留：

- source/target native outcome 与 error；
- policy/model/mapping version；
- freshness 与 input completeness；
- forbid、owner Reject、absence 和 Unknown；
- owner、issuer、source bytes 与 provenance；
- obligation、combining、time、delegation 和 round-trip 行为。

语料包含 native Unknown 被压成 no-permit、forbid 被 permit 覆盖、decision 值保留但 owner
provenance 丢失、未见 obligation failure 分支、两个 source negative 被压成一个 target
Deny。旧 mapping 发现新分歧后应自动降级并重开影响范围。

一个 corpus 全绿只能支持已运行版本和案例的 witnessed equivalence。它不能支持“统一 JSON
是 canonical”或 corpus 外语义已证明等价。

## 公平赢家条件

### Strong center

- 在 SC-U 中，真实 Authority、分权要求和 Effect 均位于声明的一致性域；通过安全与 liveness
  后，成本更低即可公平胜出。
- 在 SC-P 中，中心可以继续做最佳 coordinator，但必须取得或等待外部 owner-native
  evidence；不得以管理员写权、缓存、aggregate signature 或 workflow green 代签。
- 在 SC-E 中，必须具有 target-side fence、idempotency、readback、reconciliation 与必要
  compensation；本地 outbox green 不够。

### Mature composition

成熟组合不是“OPA/Cedar/OpenFGA/CLM/DB 标签同时出现”。它公平胜出需要：

- 至少一个实际引擎只按其原生合同运行；
- owner facts 不由 PDP 生成；
- Commitment、Reservation、Standing、target Effect 各有自己的 truth owner；
- native outcomes 先保存，再经 task-specific mapping 派生业务决策；
- 在同样 owner API、故障、预算和恢复条件下通过关键门；
- lifecycle cost 不高于正确性相同的其他臂。

其完整闭合且 candidate adapter 增量为零，是正结果。

### CLM/HITL

CLM/HITL 可以在低频、高后果协作中公平胜出，但必须展示 exact material closure、diff、
审批人 Authority role、Mandate scope、condition、reject/defer/challenge effect，并把签署
平台 audit 与应用认证链联合解释。一个 `Approve` 按钮、签署 PDF 或 controller-created
embedded signing session 不足以证明 owner Commitment。

### 人类规则

人工制度可以是最终 Authority，而不只是失败兜底。公平胜出要求规则的 owner、辖区、版本、
standing、deadline、appeal、override、理由和审计均可重建，同时测量人工分钟、排队、
disagreement、漏审、错误、恢复和认知成本。人类没有免费 oracle 特权，也不能用模糊口头
同意替代 exact-version decision。

## 语料的使用方式

`adversarial-corpus.json` 是 oracle-bearing 测试设计，不应直接作为 method fixture。推荐 runner
把每个 case 分为：

1. `public_input`；
2. 独立 owner service 按 `timeline` 在相应边界才释放的 native response；
3. method return seal；
4. 之后 evaluator 才读取 `oracle`、owner ledgers 和 target readback。

至少需要以下反作弊：

- 方法不能读取 `attack_family`、`oracle` 或 future event；
- case ID、错误时延、字段长度与签名者顺序不编码答案；
- 每个 race 在每一个命名边界后实际触发，而不是预先写成 stale label；
- positive liveness cases 与 negative cases 都必须存在；
- 强中心、成熟组合、CLM/HITL、人类规则和 candidate 使用相同 Authority、信息、预算与
  target enforcement；
- 未实际接入的 OPA/Cedar/OpenFGA/XACML 必须标 `NOT_RUN`，不能由本地 shape 代表产品。

## 最强反例与研究影响

最强反例是：

> U 与 P 拥有 byte-identical 技术权限、输入、工具、成本和中心实现；U 中所有 Authority
> 真正属于中心 Principal，P 中只有一个 external non-delegable right。若中心在两侧都通过，
> 它证明的只是技术可写，不是 Authority 合法闭合。

第二个独立反例是：

> 所有 owner read/re-read/sign/reserve 都曾正确，最后一个 owner 在各自最后检查之后撤销；
> target 又忽略或遗失 fence。局部证据、aggregate signature、reservation 和 workflow
> 全绿，仍产生 stale Effect。

这两个反例共同阻断以下伪成功：

- 免费 registry；
- 同权限等于统一 Authority；
- 顺序重读等于跨域原子快照；
- token issued 等于 target fenced；
- exact main digest 等于完整 material closure；
- challenge 表存在等于 affected-party coverage；
- migration corpus 绿等于一般语义等价。

它们不证明必须自研。相反，若成熟组合、强中心或人工制度在相同分母下正确处理这些情况，
G5 residual 可以继续为零。

## 仍未运行

- 本文件没有启动 OPA、Cedar、OpenFGA 或 XACML；
- 没有真实 owner、CLM、HITL、外部 target 或产品集成；
- 没有执行 corpus，所有 outcome 都是待实现 evaluator 的 oracle 草案；
- 没有改动 `NOW.md`、`PROGRAM.md`、LineContract、Problem 或任何正式状态；
- 没有建立 canonical IR 或机制候选。
