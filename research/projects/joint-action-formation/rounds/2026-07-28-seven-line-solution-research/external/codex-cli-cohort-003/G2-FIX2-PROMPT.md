# G2 第二次根红灯修复

读取 `COMMON.md`、`G2-PROMPT.md`、`G2-FIX-PROMPT.md`、`G2-fix-final.md` 与
`ROOT-LIVE-AUDIT.md`。这是 G2 独立 CLI 主线的第三轮。

实际建立 A/B/C：A 重建 signed response 与 request/constitution/trust 的精确绑定；B 实现；
C 独立复核 request kind/payload、operation ids、freshness、全 Unknown relation 与
self-configured platform truth。只可修改 `g2-relation/` 和本目录 `G2-fix2-final.md`。

根审计已经确认：

- Ed25519 exact raw signature 数学上成立，但 child 自生成 key、profile/endpoint 由 test
  config 指定；它不是现实 owner/platform 信任锚；
- `_verify_for_request` 未完整绑定 request `kind`、canonical request payload/hash、
  operation IDs、schema/freshness/ordinal；本地自持签名来源可对 EXPLAIN_BACK 返回 CLAIM；
- 五 owner 全部 Unknown 时仍生成
  `DERIVED_SNAPSHOT_OF_VERIFIED_EXACT_BOUND_OWNER_EVIDENCE` RelationVersion；
- T5 proof/readback 来自同一个 self-configured process/profile，
  `platform_native_scope_verified=true` 容易被误读为平台现实真值。

必须：

- receipt preimage 与 verifier 绑定 exact request kind、canonical request bytes/hash、
  endpoint、operation IDs、schema、ordinal/freshness；wrong-kind 自签 receipt 必须拒绝；
- 全 Unknown、未 constitution closure 时不得使用已 constituted 的 evidence status；
  返回无版本或 `DERIVED_CANDIDATE_WITH_UNRESOLVED_CONSTITUTION`，下游不可当 Relation
  成立；
- T5 改为 `LOCAL_FIXTURE_SELF_ASSERTION_VERIFIED` 或建立明确 pinned trust root；不得把
  ephemeral self-key 描述成真实 platform-native truth；
- owner evidence 同样明确为 local synthetic ephemeral-key conformance，不宣称 real owner
  identity、Authority 或 legal sufficiency；
- 保留五 child actual PID/key uniqueness、exact raw Ed25519、refusal/opposition、
  G5/G6 unverified 与原 46 项风险覆盖；
- 输出 G2 line-local envelope，不透传合同成功、Authority、Effect、Acceptance/Settlement。

真实 PKI/owner/platform、G5/G6 与完整 CE-001 仍为 `NOT_RUN/NOT_ESTABLISHED`。
