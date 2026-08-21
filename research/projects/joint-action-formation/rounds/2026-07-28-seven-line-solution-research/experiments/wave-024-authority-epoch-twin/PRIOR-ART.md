# Wave 024：成熟技术保证与 residual 核验

核验日期：2026-08-01  
状态：`PRIMARY-SOURCE REVIEW / DESIGN INPUT / NO RUNTIME RESULT`

本文件核对 Pro 返回中真正会改变 Wave 024 设计的成熟技术保证。目标不是证明 Towow 特别，
而是确认哪些现成能力可以直接采用、哪些组合后能完整解决、哪些语义仍不能由热门名词自动推出。

## 1. OAuth Token Introspection

[RFC 7662](https://datatracker.ietf.org/doc/html/rfc7662) 定义 protected resource 查询 token 当前
active state 与授权上下文；`active=true` 通常意味着 token 尚未撤销且仍在有效期。RFC 还明确
允许 protected resource 缓存响应，并指出这会牺牲用于授权决策的信息活性。

正向采用：

- 它可以作为 current token metadata 的标准查询接口；
- scope、client、subject、audience 与 active 状态可进入 Target gate 的输入。

不能推出：

- RFC 没有把 introspection response 与随后任意 Target Effect 放进同一事务；
- 因而即使禁用缓存，`active=true → owner revoke → Target commit` 的 check-then-act 竞态仍可能
  存在。这是接口边界带来的推论，不是 RFC 自己承诺失败；Wave 024 必须用 post-check/
  pre-commit cut 实测具体组合。

## 2. Serializable transaction

[PostgreSQL 当前文档](https://www.postgresql.org/docs/current/transaction-iso.html) 将 Serializable
定义为：成功提交的并发事务效果等同于某个逐一执行顺序；发现不能映射到串行顺序的依赖时会
触发 serialization failure，应用需要重试整个事务。

正向采用：

- 当 Authority fence、operation identity、Target state、Effect 与 terminal receipt 都由同一
  Target reference monitor 管理时，单一 serializable/锁定事务是本 residual 最简单的成熟解；
- unique request/semantic occurrence constraint 加事务可同时关闭重复 Effect 和 request-ID
  rebound。

边界：

- 如果 Authority head 在另一个不参加事务的系统中，Target 只在事务外读取一次 active 状态，
  Serializable 只排序 Target 本地数据，不能消除跨域 TOCTOU；
- transaction success 不等于 owner Acceptance，更不等于现实法律 Authority。

## 3. Zanzibar 与跨域 external consistency

[Google Zanzibar 论文入口](https://research.google/pubs/zanzibar-googles-consistent-global-authorization-system/)
说明其授权决策尊重用户动作的因果顺序，并在 ACL 与对象内容变化中提供 external consistency。

正向采用：

- 它证明大规模、因果一致的授权决策服务属于成熟可实现能力；
- Authority decision 的 revision/head 与 object revision 需要被共同绑定，而不是只看静态 ACL。

边界：

- 授权决策服务本身不自动成为任意外部 Target Effect 的 commit coordinator；
- 若 Effect 发生在 Zanzibar 之外，仍需让 Target 消费相同 revision/fence，或进入共享事务/
  sequencer。否则“授权查询 externally consistent”不等于“Effect commit 时仍 current”。

## 4. Spanner external transaction

[Google Spanner 论文入口](https://research.google/pubs/spanner-googles-globally-distributed-database-2/)
明确声称支持 externally consistent distributed transactions。

正向采用：

- 当 Authority mutation 与 Target Effect 真能加入同一 externally consistent transaction 时，
  它提供跨节点共享线性化顺序的成熟实例；
- 这说明严格跨域语义并非原则上不可能，但要求改变参与域与提交架构。

边界：

- 把两个独立外部系统分别写入、最后由 controller 拼 receipt，不是 distributed transaction；
- Spanner 也不替 owner 作 Acceptance，不证明真实组织愿意让两域共享事务。

## 5. Durable workflow 与 Target-side idempotency

[Temporal Activity 文档](https://docs.temporal.io/activity-definition) 明确说明：Activity 成功执行但
worker 在上报服务前崩溃时，Activity 会被重试；因此写操作应具备幂等性。文档还指出 idempotency
key 应由 Activity 调用的服务执行，而不是由 Activity 自己宣称。

[Stripe Idempotent Requests](https://docs.stripe.com/api/idempotent_requests) 提供成熟实例：客户端用
idempotency key 安全重试；服务端保存首次请求的 status/body，并在相同 key 参数不一致时拒绝。

正向采用：

- ACK lost/crash recovery 应使用稳定 operation ID + request digest；
- Target 返回原 terminal receipt，不能由恢复 controller 生成新 ID 或重写成功；
- attempts 可以多次，但 exact semantic Effect 必须至多一次。

边界：

- idempotency 只解决重复 Effect；它不证明 commit-time Authority；
- 最终状态相同不能证明 Effect 只发生一次，仍需 Target-native attempt/effect ledger 与 actor/
  Authority provenance；
- workflow history 不是 Target 或 owner 的权威事实源。

## 6. 当前组合判断

在 Wave 024 的 `Target-consumed fence` 作用域内，现成技术组合已经足够形成一个完整候选：

```text
versioned signed delegation/revocation
+ Target durable monotonic fence
+ Target-local atomic guard-and-commit transaction
+ stable operation ID/request digest/idempotent terminal ledger
+ Target-native status/readback
+ owner-native Acceptance/finality
```

它是否在本地 runner 中真的成立，仍须由 S/R run、post-check/pre-commit cut、对称 ACK drop/
termination、独立 evaluator 和红队 mutation 验证。若通过，正确结果是成熟组合的
`POSITIVE_SCOPED_SOLUTION`，不是 Towow 独占机制。

若要求“owner 在任意远端完成 revoke 后，所有 Target 立即停止”，现有材料只给出三类可达选择：

1. 共享 transaction/consensus/sequencer；
2. exact one-shot delegated right，使 consume/cancel 在 Target 原生账本竞争；
3. honest lease semantics，接受撤销延迟并重写保证。

不选择其中之一，就没有足够顺序事实；继续添加 RAG、目录、签名字段、manifest 或 controller
日志不会消除结构性竞态。
