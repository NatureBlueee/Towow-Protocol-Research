# Wave 015 TargetOperationLedger 合同

状态：`RUNNER FOUNDATION / LOCAL DIGITAL TARGET`

## 目的

`TargetOperationLedger` 是其 target state 的唯一 mutation truth owner。它用成熟 SQLite
transaction 和 CAS 消除一个有界 causal-twin：

> exact authorized request 已经发出、最终状态也满足 Q，但真正提交状态变化的是 H 而不是
> 当前 arm 时，不能把结果错误归因给当前 arm。

任务结果与 arm 因果贡献分开：

```text
TaskOutcomeSatisfied
AuthorizedExecutionCommitted
EffectAttributableToArm
```

H 已经产生同一终态时，任务结果可以为正，但当前 arm 必须得到
`ALREADY_SATISFIED / mutation_applied=false / commit_actor_id=H`。

## 权威状态与原子边界

每个 target 保存：

```text
target_id
state / state_sha256
version
last_commit_id
last_commit_actor_id
last_request_sha256
```

每次 mutation 使用独立 SQLite connection 和 `BEGIN IMMEDIATE`。下列动作位于同一 write
transaction：

1. 查询 authoritative pre-state；
2. 验证 exact-target、exact-actor、exact-state one-shot capability；
3. 判断 idempotent request、replay、already-satisfied 或 version conflict；
4. 对 `expected_version` 执行 CAS；
5. 更新 target state/version；
6. 消费 capability；
7. 写入 commit provenance；
8. 写入完整 authenticated receipt。

如果数据库提交成功但调用者没有收到响应，使用相同 `request_id` 和相同 request bytes
重试时必须返回完全相同的 stored receipt，不产生第二次 mutation。

## 决定语义

### `COMMITTED`

- exact capability 有效且未消费；
- authoritative state 不等于 desired state；
- `expected_version == current_version`；
- ledger 原子提交 mutation；
- `mutation_applied=true`；
- `commit_actor_id == request.actor_id`。

### `ALREADY_SATISFIED`

- authoritative current state 已等于 desired state；
- 当前请求没有产生 mutation；
- receipt 指向实际拥有当前 state 的既有 `commit_id/commit_actor_id`；
- capability 作为已接受的终止调用被一次性消费；
- 不得把当前 actor 写成 Effect 原因。

这项判断优先于 version conflict，用于显式识别 H-first 相同终态。

### `CONFLICT`

- current state 尚未满足 desired state；
- `expected_version != current_version`；
- 不发生 mutation，也不消费 capability；
- 调用者可以读取新 state 后以新 request 决定是否重试。

### `REPLAY_REJECTED`

至少包括：

- 相同 `request_id` 被改写 actor、capability、target、version 或 desired state；
- one-shot capability 被另一个 request 再次使用；
- capability 的 actor、target、operation 或 allowed state 不匹配；
- capability 不存在。

## Receipt

每个 receipt 至少绑定：

```text
ledger_id / receipt_id
decision / reason / mutation_applied
actor_id / request_id / request_sha256
capability_id / target_id / operation
expected_version
pre_state / pre_state_sha256 / pre_version
post_state / post_state_sha256 / post_version
commit_id / commit_actor_id
receipt_sha256 / receipt_auth_hex
```

`receipt_sha256` 防普通字节误改；`receipt_auth_hex` 使用 ledger 私有 HMAC key 证明 receipt
来自该 truth owner。验证还要求 receipt 与数据库内的原始 stored receipt 完全一致。

HMAC key 当前与 SQLite truth owner 位于同一权限域。这不是抵抗可重写数据库和 key 的恶意
同用户/DBA 的外部不可篡改证明。

## Readback

readback 必须绑定 exact：

```text
receipt_id / receipt_sha256
request_id / request_sha256
actor_id / capability_id / target_id
receipt decision / mutation_applied
receipt commit_id / post_version
observed state/version/commit_id/commit_actor
attached_to_receipt_commit
```

默认验证要求 observed state 仍位于该 receipt 的 exact commit。如果随后发生合法新 commit，
旧 receipt 的新 readback 可以作为真实历史观察保存，但不得作为 exact attached readback
接受。

## 必须通过的攻击

- `H-first`：H 先产生相同终态，A4 得到 `ALREADY_SATISFIED`，不能获得因果归因；
- 真实并发：两个独立 connection 从相同 expected version 竞争，最多一个 mutation commit；
- exact request replay：返回同一 receipt，不产生第二 commit；
- capability replay：新 request 使用已消费 capability 得到 `REPLAY_REJECTED`；
- receipt transplant：另一 ledger/truth owner 拒绝；
- actor relabel：即使重算公开 SHA-256，HMAC/stored identity 仍拒绝；
- readback detach：readback 不能从一个 receipt 移接到另一个 receipt 或后继 commit。

## 正向结果解释

若上述实现和攻击通过，成熟 transaction/CAS/capability/receipt 组合在声明的本地数字
target 边界内就是正向有界解：

```text
EXISTING_MATURE_TARGET_LEDGER = POSITIVE_SCOPED_SOLUTION
CAUSAL_TWIN_WITHIN_THIS_DIGITAL_TRUST_BOUNDARY = CLOSED
```

这不会降低通爻价值，也不要求再创造同范围的新 mutation 机制。它可以作为 A0–A5 的共同
target-native primitive；后续公平比较应把 causal closure 归因于该 primitive，而不是
任一 coordinator 的独占能力。

## 当前明确不负责

- 现实电路、发电机、actuator 或 meter 的物理 Effect；
- capability issuer 是否拥有合法 Principal Authority；
- 真人理解、Adoption、Acceptance、Settlement；
- target 之外的未记录 mutation path；
- 恶意 DBA、同用户数据库与 HMAC key 协调重写；
- TPM/TEE、secure clock、hardware monotonic counter；
- 跨数据库或跨组织的 distributed atomic commit；
- provider 停更、迁移、格式出口与长期维护成本；
- CE-001 其余 case、A0–A5 完整比较或 V1/V2 一般解。
