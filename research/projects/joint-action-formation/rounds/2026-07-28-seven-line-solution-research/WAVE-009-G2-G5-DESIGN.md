# Wave 009 Unit B — G2 relation truth and G5 authority truth

日期：2026-07-29  
状态：`INDEPENDENT DESIGN COMPLETE / NOT RUN`

## 两条线为什么不能压成一个 green state

G2 判断共同关系是否、以什么 horizon 和哪个版本形成；G5 判断某个精确动作在当前时刻是否
获得正确主体的授权、承诺和资源条件。它们可以共享原始事件，但必须由两个 truth owner
分别评价。

每个 transition 都绑定：

`principal_id / actor_entity / controller / exact version+hash / scope / time / provenance`

语义固定为：

- proposal 只是候选；
- ack 只证明收到；
- explain-back 只证明当前理解；
- counter 产生候选变化，不构成接受；
- commit 是规范承诺，不等于资源可用；
- reserve 是资源账本状态，不扩大授权；
- revoke 使依赖该授权的未来动作失效，不删除历史关系。

## 冻结变量

### G2 Relation truth

- horizon：`ONE_SHOT / BOUNDED(k, expiry, purpose) / DURABLE`；
- 当前 RelationVersion；
- role、action、purpose、evidence、exit、evaluation schema fingerprint；
- 参数更新、语义等价改写或 material change；
- 每个 Principal 对精确版本的 proposal/ack/explain-back/counter/stance；
- contribution provenance 与局部 opposition；
- formation condition；
- CMMN/CLM 编译到 BPMN/policy 后的 semantic loss；
- 固定制度是否根本不需要新关系。

### G5 Authority truth

- Principal、Agent Entity、controller、Authority Locus 映射；
- action/purpose/resource/time/counterparty/RelationVersion scoped Mandate；
- signature、budget、data、resource、Acceptance authority；
- Commitment 条件；
- Reservation 的资源、时间窗、唯一性、lease、expiry；
- revoke head 和生效顺序；
- 受影响方 Standing；
- controller 是否拥有代行权。

## 当前最强现成组合

1. CMMN 管理未定型、允许 amendment 的 case，稳定片段编译为 BPMN，并保留 HITL；
2. CLM/approval 保存 proposal、counter、精确合同版本、签署和撤销；
3. OpenFGA 保存 relation/role tuple，Cedar 或 OPA 评价 action/context policy；
4. scoped delegation/token 把动作、用途、资源、期限和对手方绑定到 Principal-issued authority；
5. Commitment record 与 transactional Reservation ledger 分离，reservation 使用 unique
   constraint、idempotency key、lease 和 expiry；
6. append-only event/provenance log 保存原始字节、版本头、贡献、撤销与执行 readback；
7. authority-aware strong center + HITL 负责查询、编排和异常升级，但不替 Principal
   生成 ACK、approval 或 acceptance，也不成为第二 truth source。

公平基线：

- `B0`：同信息、工具、查询预算和拒绝权的强中心 + HITL；
- `B1`：CMMN/BPMN + HITL；
- `B2`：CLM/approval；
- `B3a/B3b`：OpenFGA+Cedar / OpenFGA+OPA；
- `B4`：Commitment + transactional Reservation；
- `B5`：上述成熟构件的完整组合；
- `B6`：B5 + 最小 Relation/Authority adapter，只用于检验残余。

若 B0 或 B5 完整解决，就是通爻的正向方案；B6 增量为零不构成失败。

## 精确待证缺口

G2 只保留三个问题：

1. 未预编码 schema 时，在相同查询与披露预算下能否区分参数变化、同义改写和隐藏的
   role/action/purpose/evidence/exit/evaluation material change；
2. CMMN/CLM 向 BPMN、policy 或中心摘要编译时，能否保留多作者来源、局部 scope、
   未决反对和精确版本；
3. 能否正确区分 one-shot、bounded reuse 和 durable relation，既不过度物化，也不丢失
   amendment、exit 和责任语义。

G5 只保留四个问题：

1. policy 所用事实由谁产生、认领和撤销，能否追到真实 Principal/Authority Locus；
2. stance、Mandate、Commitment、Reservation 与 revoke head 跨系统组合时，能否成为唯一、
   原子、可恢复的 gate；
3. 没有最终签字权但会受影响的主体，其 Standing/challenge/recourse 能否被发现并执行；
4. controller 能否在任何路径用摘要、账户、workflow completion 或 `Allow` 替换 Principal
   的 ACK、授权、承诺或接受。

成熟组合若在留出 world 中无损解决，缺口就是零，不创建新对象。

## Paired worlds

事件序列统一为：

`proposal → ack → explain-back → counter → exact-version stance/commit → reserve →
revoke/current-head check → execution gate`

| Pair | 唯一差异 | G2 预期 | G5 预期 |
|---|---|---|---|
| P1 one-shot/bounded | B 多双方签署的 reuse/purpose/expiry/exit | one-shot vs bounded | 首次授权相同也不推出复用关系 |
| P2 bounded/durable | B 多 amendment/governance/evidence/exit/renewal | 到期关闭 vs durable v | 当前 action mandate 可以相同 |
| P3 parameter/material | 日期变化 vs no-training→允许衍生训练 | 不重开 vs 创建 v2 | material world 旧 mandate 失效 |
| P4 retained/lost | 编译保留或丢失 exit/evidence/opposition | 丢失必须报错 | G5 不替 G2 判断语义 |
| P5 current/stale | 相同 v2 proposal；一方只有 v1 stance | v1 不继承 v2 | permit vs stale |
| P6 unique/duplicate | 相同 Commitment；一个或两个竞争 reservation | Relation 相同 | duplicate 必须阻断 |
| P7 Principal/controller | Principal 直签 vs controller 代填 | provenance 不同 | substitution 必须失败 |
| P8 active/revoked | 相同旧 token/workflow；revoke 生效顺序不同 | 历史关系可仍成立 | revoked 不得执行 |
| P9 crossed square | durable 但无当前授权/资源 vs one-shot 有合法 gate | DURABLE vs ONE_SHOT | DENY vs PERMIT |
| P10 fixed/open | T5 固定平台 vs T3/T4 未定型合作 | 前者旁路 relation | 前者复用平台 authority |

## 两个 evaluator 与非蕴含门

`RelationEvaluator` 只输出：

- stage：`NONE / PROPOSAL / COUNTER_PENDING / FORMED`；
- horizon：`ONE_SHOT_EPISODE / BOUNDED_RELATION / DURABLE_RELATION`；
- current version/hash；
- material-change、stale stance、semantic loss；
- source/scope/opposition retention；
- over/missed materialization；
- 查询、披露、人工、版本与治理成本。

它不得输出 `ALLOW`、Mandate、Commitment、Reservation、Effect 或 Acceptance。

`AuthorityEvaluator` 只输出：

- `PERMIT / DENY / REQUIRE_APPROVAL / STALE_VERSION / REVOKED /
  RESERVATION_REQUIRED / UNKNOWN`；
- `mandate_valid / commitment_valid / reservation_unique_current / standing_respected`；
- false allow/deny、stale acceptance、revoke propagation、duplicate reservation、
  controller substitution 和维护成本。

它不得判断 Relation 是否形成、horizon 或 materiality。

强制非蕴含：

- G2 FORMED 不蕴含 G5 PERMIT；
- G5 PERMIT 不蕴含 Relation、共同理解、Commitment、Reservation、Effect 或 Acceptance；
- ACK ≠ explain-back ≠ stance/acceptance；
- proposal/counter ≠ Commitment；
- Commitment ≠ Reservation；Reservation ≠ Mandate；
- durable relation ≠ future blanket authority；
- action mandate 撤销不删除历史 RelationVersion；
- G2 判断 material change 不决定谁有权接受变化。

第三个 integration evaluator 只能消费两个公开输出；只有当前 task/relation version 与 exact
action mandate、Commitment、Reservation 全部成立时才输出 `EXECUTION_READY`，且不能反向
晋升 G2/G5。

## 最强反例

T4 三方投标形成 v1 后，成员 B 把“买方域只读、no-training”改成“供应商可保留并训练
衍生物”，同时改变数据 Authority、证据义务和退出条件，形成 material v2。

controller 把它摘要为字段更新，使 CMMN/BPMN 走旧路径；CLM 显示 v2，但 A 的 stance、
预算 approval 和数据 Mandate 仍绑定 v1；policy engine 因认证账户和角色返回 Allow；两个
并发投标重复预留同一资源；资源 owner 已撤销授权；最后 controller 用 workflow completion
代替 Principal approval。所有局部系统都可显示绿色，但整体动作不合法。

其 crossed-square 对照更锐利：

- world A：durable relation 成立，但当前预算权已撤销且没有 reservation，应为
  `G2=DURABLE, G5=DENY`；
- world B：没有 durable relation，但有合法 one-shot mandate 和唯一 reservation，应为
  `G2=ONE_SHOT, G5=PERMIT`。

任何把 Relation 与 Authority 压成一个 green/ready 状态的方案至少错判一个。

## 下一实现

1. 独立 `RelationTruthBroker` 与 `AuthorityTruthBroker`，使用 opaque world/run ID、独立
   signing key 和私有状态；
2. 核心 crossed-square：
   `T3/T4 × 3 horizons × relation-valid/invalid × authority-valid/invalid = 24 worlds`；
3. 追加 parameter/material、retained/lost、current/stale、unique/duplicate、
   Principal/controller、active/revoked mutations 和 T5 bypass；
4. 所有 baseline 使用相同事件 schema、原始字节、Principal 查询预算和 operation 计费；
   先实现 B0–B5，观察真实残余后才实现 B6；
5. 两 evaluator 不能 import 或调用对方 truth broker，integration 只读公开输出；
6. parent 记录 exact bytes/hash、keys、raw operation、policy decision、ledger transaction
   和退出状态；
7. 首个留出同时包含“相似措辞但 materiality 不同”和“措辞不同但语义等价”，防止关键词路由；
8. 实现后由不同 Agent 攻击 controller substitution 和并发 reservation。

本设计尚未运行，现有组合覆盖率与 B6 增量均为 `NOT_RUN`。
