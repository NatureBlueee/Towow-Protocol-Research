# Wave 018 E4 actual-process contract

状态：`LOCAL_SYNTHETIC / ACTUAL PROCESS / EXISTING-COMPOSITION TEST`

## 受检验的有界主张

在 REMAINING-CASE-CONTRACTS 的 E4 synthetic world 中，primary resource 已真实 reserve
但在 Target commit 前 owner-native revoke；若另一独立 owner 的 alternative 只在 revoke
后通过实际 rediscovery 出现，则现成的 revoke、局部依赖失效、compensation、registry、
owner-native receipt、fresh status query 与 durable idempotent Target ledger 组合，能否：

1. 不消费 stale primary receipts；
2. 只重开受 primary revoke 影响的 descendants；
3. 为 alternative 独立形成 offer、grant、commitment、reservation；
4. 重新取得 exact venue/safety approval 和 O_P binding；
5. 在 commit-time 重新向 owner truth 查询 current heads；
6. 对 `VenueV:CircuitC7` 只产生一次 exact occurrence/readback；
7. 获得 O_Q/O_V 双 Acceptance 与 alternative-bound finality。

这是 `LOCAL_SYNTHETIC_E4_EXISTING_COMPOSITION` 主张，不证明现实发电机、法律 Authority、
真人 Adoption/Acceptance、物理 Effect 或跨域普遍性。合同中的
`RECOVERED_VIA_LEGAL_ALTERNATIVE` 是继承的 terminal disposition 名称，不是本实验对法律
有效性的证明。

## 隐藏与独立性要求

- arm public startup 不包含 E4 label、alternative identity、排序、owner handle、key、
  principal 或预期结果。
- primary 与 alternative 必须是不同 spawn process、Ed25519 key、state source 和
  principal。
- alternative 只能由 revoke 后第二次 `DISCOVER` 的 opaque handle 得到；arm 不允许从
  controller 启动包预选。
- Target、Broker、ARM、六个 owner 共九个实际 spawn process。
- evaluator 不导入 runtime helpers；canonicalization、SHA-256、Ed25519、exact coordinates
  与 SQLite facts 均独立重验。

## Commit-time current gate

Target 在 durable mutation 前直接查询下列 owner endpoints，并将 signed status hashes
绑定进 occurrence：

| owner | status 必须观察的 head |
|---|---|
| RESOURCE_ALTERNATIVE | alternative reservation `state_head_after` |
| O_V | exact venue reapproval `state_head_after` |
| O_S | exact safety reapproval `state_head_after` |
| RESOURCE_PRIMARY | owner-native revoke `state_head_after` |
| O_P | alternative obligation binding `state_head_after` |

RESOURCE_ALTERNATIVE 必须 `current=true/reserved=true/revoked=false`；primary 必须
`current=false/revoked=true`。O_P binding 的 `state_head_before` 必须等于 primary
compensation 的 `state_head_after`。

## Target exact truth

Target 复用 Wave 015 `TargetOperationLedger` 的 SQLite transaction/CAS、one-shot capability、
stored HMAC receipt 和 attached readback。运行时 WAL 数据库不能直接作为冻结证据；运行
结束后必须使用 SQLite backup API 复制到新的 DELETE-journal 数据库。冻结 evaluator
必须拒绝 WAL header、`-wal/-shm/-journal` companions，并同时绑定整文件物理哈希与按
schema/table/primary-key 排序重建的逻辑内容哈希。成功世界必须从该独立数据库验证：

- object：`VenueV:CircuitC7`；
- effect window：minute 10 到 55，共 45 minutes；
- deadline：minute 90；
- 46 个 offset samples：`0..45`；
- 每个 sample 的 absolute minute 为 `10 + offset`；
- power 在 3kW 的 ±5% 区间；
- 每个 sample `safety_ok=true`、`noise_ok=true`；
- 每个 sample `other_circuits_energized=[]`；
- `commit_events=1`、`readbacks=1`、one-shot capability 只消费一次；
- 相同 semantic request replay 返回同一 stored receipt，不能产生第二 mutation。

## 反事实与攻击

`REMOVE_ALTERNATIVE` 只从 Broker inventory 移除 alternative，保持 process topology、startup
shape、primary reserve/revoke 与其他机制不变。正确结果是
`BOUNDED_REFUSAL_NO_ALTERNATIVE`、Target version 0、零 commit/readback、capability 未消费。

必须拒绝：

- stale primary chain；
- controller startup preselection；
- revoke 后不执行 rediscovery；
- wrong alternative owner key；
- global/unbounded reopen；
- alternative removed 仍报告 success；
- duplicate Target mutation。
