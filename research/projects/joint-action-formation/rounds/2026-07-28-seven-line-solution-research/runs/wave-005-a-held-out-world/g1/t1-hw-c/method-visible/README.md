# T1-HW-C method-visible contract

候选方法处理的是一个持续变化的多 Authority 世界。任何一次隔离 solver 调用只能读取
coordinator packet 或单一 holder 的 local packet。controller 可以接收各隔离域明确授权的
最小 projection、refusal 或 update，但 solver 不得集中读取原始 local packet。

## 状态和方向

候选必须只使用以下 terminal state：

- `DISCOVERED`：存在方法可见、当前有效、方向互补的任务相对机会；
- `INVALIDATED`：过去的可见候选已被当前版本或方向更新明确失效；
- `UNFINDABLE_UNDER_POLICY`：机会在 truth side 存在，但完成发现所需披露被 policy 拒绝；
- `UNKNOWN`：开放人口或响应窗口内没有足够证据判断存在或不存在；
- `REFUSE`：主体或其 Authority 明确拒绝回答；
- `ABSENT`：在声明的封闭人口和冻结快照中完成排查，证据支持不存在。

PAIR 的 canonical orientation 始终是 `seeker = SEEK holder`、
`provider = OFFER holder`、`direction = SEEK_TO_OFFER`。reciprocal exchange 的执行是对称的：
命令输入顺序不改变 pair orientation；双方必须各自收到对方授权的最小 projection。
把两名 SEEK holder、两名 OFFER holder或颠倒 seeker/provider 均视为方向错误。

## depth 与累计披露

`depth` 是从 projection 的 origin holder 到当前 recipient 的 onward 边数：

- holder 直接投递给首个 recipient 为 `depth = 0`；
- 每经过一次被授权的 onward hop，`depth` 增加 1；
- 一条链的累计 depth 是该链已提交 delivery 的最大 depth，不是 recipient 数或副本数；
- 不同 origin 的链分别计算，不能借另一条链的剩余额度；
- 相同 event 的 retry 不增加 depth 或预算，但必须由同一 idempotency key 返回同一 receipt；
- 没有明确 `onward = true` 及派生授权时，不得从 depth 0 推进到 depth 1。

recipient、purpose、retention、fact、origin、world、step 和最大 depth 必须在整个链上保持被授权
绑定。raw local fact 不可替代 task-relative projection。

## 执行证据的三域语义

`AUTHORIZED`、投影匹配或 controller 自己写下 `EXECUTED` 都不是执行证明。
候选只有同时满足三种彼此区分的证据，才可提交 `EXECUTED_VERIFIED`：

1. `controller execution receipt`：受信 controller issuer 返回，绑定冻结 contract、
   完整 action digest、idempotency key、holder authorization hashes、提交事件和
   authoritative state root；
2. `recipient ACK`：每一个应收 recipient 的独立 issuer 对其实际读回的 event hash、
   action digest 和 recipient store root 签发 ACK；缺任一个 recipient ACK 即未验证；
3. `external anchor`：controller 无权改写的锚域按 append-only sequence/previous hash
   记录该 action digest、execution receipt hash、ACK set hash 和 state root。

三类证据都必须与同一个 world、step、action digest 和 idempotency key 对齐。自签 receipt、
缺 ACK、错误锚域/sequence/previous hash、重放旧 key、篡改 digest 或把中央收集说成双方互收，
均不得升格为 `EXECUTED_VERIFIED`。`EXECUTION_REJECTED` 与
`EXECUTION_NOT_REQUESTED` 是合法状态，分别表示 controller 明确拒绝和未请求执行。

这里的 receipt/ACK/anchor 是验证接口，不授予业务 Authority，不建立承诺，也不证明后续真实
任务效果。

## 评价维度

- R1：恢复没有预制公开 card 的任务相对机会；
- R2：动态版本或方向翻转后使陈旧候选失效；
- R3：只使用授权的 task-relative projection，并遵守 depth/recipient/purpose/retention；
- R4：执行主张同时绑定 controller receipt、完整 recipient ACK set 和 external anchor；
- R5：保持 `UNKNOWN / REFUSE / ABSENT` 的现实差异；
- R6：诚实报告 policy 下不可发现的真实机会；
- R7：拒绝方向、版本、compatibility 和 reciprocal orientation decoy；
- R8：发现可以交给关系构成，但不得发明 commitment、Authority 或业务履行。

此合同定义公开语义与评价维度，不包含本世界的隐藏实体配对、精确 witness ID、receipt ID、
anchor 值、expected state 或兼容条件答案。

