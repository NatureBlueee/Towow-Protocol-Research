# G2 第二次根红灯修复

日期：2026-07-30  
状态：`LOCAL SYNTHETIC EXACT REQUEST-RESPONSE BINDING REPAIRED /
CONSTITUTION AND TRUST OVERCLAIM REPAIRED / INDEPENDENT ATTACK RECHECKED /
NO FULL CE-001 RUN / NO FORMAL PROMOTION`

实现目录：
`experiments/wave-012-ce001-power-restoration/g2-relation/`

## 结论

第三轮关闭了根审计指出的四类缺口，并保留了第二轮已经成立的 exact raw Ed25519、
五 child actual PID/key uniqueness、refusal/opposition、G5/G6 unverified 与原 46 项风险
覆盖：

1. signed response 现在绑定 actual canonical wire request bytes/base64/SHA-256、
   request payload hash、request/receipt schema、requested kind、endpoint、relation schema、
   episode-specific operation IDs、global/per-process/issuer ordinal、nonce 与 UTC freshness；
2. self-signed wrong-kind、payload、operation、schema、endpoint、ordinal、freshness 或 replay
   response 均 fail closed；
3. RelationVersion 先计算五 owner exact constitution closure。全 Unknown、refusal、坏签或
   wrong binding 时只生成
   `DERIVED_CANDIDATE_WITH_UNRESOLVED_CONSTITUTION`，明确
   `relation_established=false`、`downstream_relation_gate_open=false`，不生成
   `AUTHORIZE/ACTIVATE`；
4. owner/platform key 都明确为 child 启动时自生成的
   `LOCAL_SYNTHETIC_EPHEMERAL_SELF_KEY`。T5 proof/readback 只分类为
   `LOCAL_FIXTURE_SELF_ASSERTION_VERIFIED`，不再输出
   `platform_native_scope_verified=true`；
5. G2 输出增加 allowlisted `g2_line_local_envelope`，不透传合同 success、Authority、
   Effect、Acceptance 或 Settlement；
6. C 独立发现 `PRIVATE_COLUMN_UNKNOWN` 被 verifier 拒绝后由 controller 补 Unknown 的
   provenance 红灯。根会话没有改 C 的测试，只修 response-kind allowlist；现在 O_R 的
   signed Unknown act 被保留，同时 relation gate 仍关闭。

当前最强结论是：

```text
G2_EXACT_LOCAL_REQUEST_RESPONSE_CONFORMANCE = POSITIVE_SCOPED
G2_LOCAL_EPHEMERAL_KEY_RAW_ED25519 = POSITIVE_SCOPED
G2_ACTUAL_CHILD_PID_KEY_UNIQUENESS = ATTACK_RECHECK_PASS
G2_ALL_UNKNOWN_RELATION_GATE = FAIL_CLOSED
G2_PRIVATE_COLUMN_UNKNOWN_PROVENANCE = VERIFIED_LOCAL_EPHEMERAL_OWNER_UNKNOWN
T5_PLATFORM_ASSERTION = LOCAL_FIXTURE_SELF_ASSERTION_VERIFIED
REAL_PKI = NOT_RUN
REAL_OWNER_IDENTITY = NOT_ESTABLISHED
REAL_PLATFORM_IDENTITY_APPLICABILITY = NOT_ESTABLISHED
G5_AUTHORITY = UNVERIFIED
G6_EFFECT = NOT_RUN
ACCEPTANCE = NOT_RUN
SETTLEMENT = NOT_RUN
FULL_CE001 = NOT_RUN
CE001_COMPLETE_SOLUTION = NOT_ESTABLISHED
```

## 实际 A / B / C

| identity | 职责 | 实际结果 |
|---|---|---|
| `/root/g2_fix2_a_binding` | A：只读重建 request/receipt、constitution 与 trust 边界 | 复跑旧 `46/46`；用内存自签探针证明 wrong-kind、wrong operation、wrong schema/ordinal/time 均可被旧 verifier 接受；确认全 Unknown 仍生成 constituted-looking RelationVersion；未改文件 |
| `/root/g2_fix2_b_implement` | B：实现 v3 request/receipt、constitution gate、trust classification 与 line-local envelope | 新增 8 项 fix2 攻击；交付时 `54/54 PASS`；未运行 runner、未改旧 outputs |
| `/root/g2_fix2_c_independent` | C：不继承 A/B 对话，独立攻击公开接口 | 新增 13 项独立攻击；首轮定向 `12/13`、合并 `66/67`，保留 `PRIVATE_COLUMN_UNKNOWN` provenance 红灯及 `C-FIX2-ATTACK.md`；未改生产实现或 outputs |

根会话重读正典与全部实现，复跑原基线，检查 B 的 signed preimage/verifier，修复 C 的
Unknown provenance 红灯，将全 Unknown 纳入 persisted fixture，重建双跑证据并完成最终
source/readback 验证。

A/B/C 共享模型家族、仓库、本机用户和研究传统。它们提供职责与失败路径隔离，不构成现实
组织、独立实验室或外部权限域复现。

## Exact request-response binding

controller 生成的 request 是当前 verifier 的 canonical truth source，包含：

```text
request_schema_version
query_id / run_id / episode_id
request_ordinal / process_ordinal
request_nonce / issued_at / expires_at
owner_id / endpoint_binding
kind
exact Q / object / purpose
relation revision/hash/version hash/schema hash
scope
episode-specific operation_ids
request_payload
```

child 对 response preimage 作 exact raw Ed25519 签名；preimage 除保留 owner、Q、object、
revision、source 与 process identity 外，还签入：

```text
receipt_schema_version
requested_kind / response kind / decision
canonical request raw bytes/base64/SHA-256
request payload SHA-256
endpoint binding/hash
operation_ids
request/process/issuer ordinal
nonce / request freshness window / signed_at
relation schema hash
```

verifier 同时执行：

- request 与 receipt schema allowlist；
- actual canonical request bytes/hash 与 payload hash 重算；
- requested-kind → allowed response-kind 映射；
- endpoint descriptor、actual `Popen.pid`、manifest、process instance、key、worker source 与
  profile source exact binding；
- operation IDs 为 exact、唯一、episode-specific ordered list，且
  `AUTHORIZE/ACTIVATE` response payload 必须原样镜像；
- relation schema hash 显式匹配；
- global request ordinal 与 per-process/issuer ordinal 严格连续；
- query id、nonce、request hash 在当前 verification state 中一次性消费；
- `issued_at/expires_at/signed_at` 为 UTC Z timestamp，窗口不超过 30 秒，拒绝 stale、
  future、malformed 与 window-outside signature。

这些门只证明当前 local fixture endpoint 对 exact request/response bytes 的 conformance。
它们不把 ephemeral key 变成现实 owner/platform identity、Authority、PKI 或法律充分性。
当前 replay registry 只在单次 controller run 的内存中；跨 run、跨 controller 持久化 replay
仍未建立。

## Constitution 与全 Unknown

RelationVersion 派生前逐 owner 计算：

```text
required owners = O_Q / O_V / O_R / O_S / O_P
exact CONSTITUTE response
decision = CONSTITUTED
current request/schema/revision binding
constitution closure
```

只有五 owner 全部满足，才得到 local fixture snapshot。任一 Unknown、refusal、坏签、
wrong binding 或缺 act，均得到：

```text
evidence_status = DERIVED_CANDIDATE_WITH_UNRESOLVED_CONSTITUTION
relation_established = false
downstream_relation_gate_open = false
may_be_treated_as_established_relation = false
```

保存的 `CE001-E2-ALL-UNKNOWN` 实际 readback：

```text
private column = signed O_R PRIVATE_COLUMN_UNKNOWN
five constitution owner states = Unknown
constitution status = UNRESOLVED_CONSTITUTION
AUTHORIZE / ACTIVATE acts = 0
contract_fields_emitted = []
```

候选仍保留 exact signed Unknown、refusal 与 opposition 原始 evidence；controller 不用绿色
关系事实覆盖这些差异。

## Owner 与 T5 trust truth

五 owner 的 public manifest、receipt、summary 与 line envelope 均明确：

```text
evidence_origin = LOCAL_SYNTHETIC_EPHEMERAL_SELF_KEY
trust_anchor_status = NOT_ESTABLISHED
real_owner_identity = NOT_ESTABLISHED
authority = NOT_ESTABLISHED
legal_sufficiency = NOT_ESTABLISHED
```

T5 的 proof/readback 来自同一个由 fixture descriptor/profile 配置的 platform child。两份
receipt 对 exact request bytes 的签名有效，但只允许解释为：

```text
verification_classification = LOCAL_FIXTURE_SELF_ASSERTION_VERIFIED
self_configured_profile_and_endpoint = true
real_platform_identity = NOT_ESTABLISHED
real_platform_applicability = NOT_ESTABLISHED
effect = NOT_RUN
```

当前没有 pinned trust root、组织证书链、HSM、外部 key registry、真实 platform API 或跨
权限域部署。

## G2 line-local envelope

每个 E2/T5 output 都单独返回 allowlisted `g2_line_local_envelope`：

```text
schema_version
line_id = G2
episode_binding
evidence_class
request_response_conformance
relation_candidate_or_snapshot
raw_evidence_refs
contract_fields_emitted = []
external_truth_status = NOT_ESTABLISHED
unverified_adjacent_lines = [G5, G6]
```

C 对 config 注入和 envelope 递归 key 扫描均未观察到合同 result/success、
`ExactTaskSuccess`、`CorrectResolution`、`contract_*`、Authority、Effect、Acceptance 或
Settlement 进入该 envelope。`authorized/activated` 仍只是 owner intent 原生坐标：

```text
authorized = G5_UNVERIFIED_OWNER_INTENT_ONLY
activated = G6_UNVERIFIED_NO_EFFECT
O_E = NOT_RUN
```

## 红灯历史

### 旧 46 项绿但 request binding 不完整

第三轮开始时旧套件为 `46/46 PASS`，但 A 的 self-signed probe 实际得到：

```text
requested kind = EXPLAIN_BACK
signed response kind = CLAIM
request operation = OP-REQUEST
signed operation = OP-WRONG
receipt schema = totally-wrong-schema
ordinal = 999
time = not-a-time
old verifier = ACCEPTED
```

同时 `MISSING_ALL` 的五 constitution owner 全 Unknown，旧实现仍返回
`DERIVED_SNAPSHOT_OF_VERIFIED_EXACT_BOUND_OWNER_EVIDENCE`。

### B 实现中间红灯

B 的第一次合并回归为 `39 PASS / 6 FAIL / 1 ERROR`。失败包括旧断言仍允许未闭合
constitution downstream、旧 persisted outputs schema/source drift、semantic projection
包含随机 revision hash，以及错误文案。B 没有把中间状态宣称为完成；修复后交付
`54/54 PASS`。

### C 独立 Unknown provenance 红灯

C 首轮：

```text
fix2 independent = 12/13 PASS
combined = 66/67 PASS
```

唯一失败：

```text
PRIVATE_COLUMN_UNKNOWN signed by O_R
→ response allowlist reject
→ controller writes UNKNOWN / REJECTED placeholder
```

这没有错误打开 relation gate，但混淆了“owner 已签 Unknown”和“无效 response 后 controller
推断 Unknown”。根会话只加入 `PRIVATE_COLUMN_UNKNOWN` allowlist entry，未改 C 的测试：

```text
C fix2 independent = 13/13 PASS
combined = 67/67 PASS
```

### persisted 分母扩展红灯

根会话将 all-Unknown 加入 persisted fixture 后，runner 双跑通过，但旧 persisted test 把
场景数硬编码为 `[6,6]`，合并测试再次为 `66/67`。测试改为从当前 `e2.json + e0.json`
计算冻结场景数并与 summary 互证；最终 `67/67 PASS`。

## 最终运行

运行命令：

```bash
cd research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-012-ce001-power-restoration/g2-relation
python3 -W error::ResourceWarning -m unittest tests.test_fix2_independent -v
python3 -W error::ResourceWarning -m unittest discover -s tests -v
PYTHONPYCACHEPREFIX=/private/tmp/g2-fix2-root-pycache python3 -m py_compile \
  g2_relation.py owner_worker.py platform_worker.py run.py \
  tests/test_adversarial.py tests/test_fix2_bindings.py \
  tests/test_fix2_independent.py tests/test_g2_relation.py \
  tests/test_root_fix_adversarial.py
python3 run.py
python3 -m json.tool outputs/summary.json >/dev/null
```

最终数字：

- tests：`67/67 PASS`，其中 C 独立 fix2 `13/13 PASS`；
- 2 次完整复跑；
- 每次 7 个 G2 diagnostic 场景：6 个 E2、1 个 T5；
- 256 份 signed receipt；
- 62 个 process instance、62 个 unique actual PID、62 个 unique Ed25519 key id；
- 62/62 child exit code 为 0；
- 784 条 trace；
- raw bytes preserved：`true`；
- semantic rerun equal：`true`；
- semantic rerun SHA-256：
  `a374a4e00548a57d675813202cf2f601cd1af0f58e11629b978e1bc1d7c15026`；
- trace canonical SHA-256：
  `f04978c7cfa5b0262fb4b76909486a6a41c18e0f4fda225b4b54dd65a5d1686d`。

关键 SHA-256：

| 文件 | SHA-256 |
|---|---|
| `g2_relation.py` | `e9dbe432e4daf61e03ffee70119d16408fe1cbfe94c8e8df37c51d54b27d9506` |
| `owner_worker.py` | `6ed3931303e60f21b0647cf18df766b153d3ed4cf879e5a945b0115791f7eb20` |
| `platform_worker.py` | `03b3674d9eff76ab82d3a4dfd5380e740612929e562eb59f317dd65b0a58092f` |
| `run.py` | `298893703a3284dfe904a555b74018e87f4c65a557789f750137c2573f8690c3` |
| `fixtures/e2.json` | `99fc0a6ec5a846ced32211a988c7d44dbd24beb1d25354ffd48062559ab2ed52` |
| `tests/test_fix2_bindings.py` | `e22debe35ca61478b921e215876e90f1ce8365ef28ce4fca832c4c54e20e205d` |
| `tests/test_fix2_independent.py` | `176e70536218b72b61fc21cb7a487bd36075a1c4b6a7e70986177aaef56809f0` |
| `tests/test_root_fix_adversarial.py` | `6d514afeacdb37bb4ad7e732aa7cf24f8891c8babe98a568712252f95e1febfa` |
| `outputs/summary.json` | `751dd5caae1bec8dde89d85952f2c0464c83f832cfe5ef855c54a19780c2df4c` |

`outputs/process-source-manifest.json` 已绑定最终 controller/worker/runner/fixture source，
persisted-evidence test 独立重算 raw receipt signature、manifest、trace、semantic projection、
source hash、PID/key 计数与 summary。

## 能支持

- 当前 local synthetic run 中，signed response 与 exact canonical request
  kind/payload/hash/endpoint/operation/schema/ordinal/freshness 完整绑定；
- wrong-kind 自签 receipt、payload/op-id/schema/endpoint substitution、stale/future/replay
  均 fail closed；
- 五 child actual PID/process/key uniqueness 与 exact raw Ed25519 未回退；
- owner signed Unknown、ABSENT、WITHHELD、DISCLOSED、refusal 与 opposition 的 provenance
  差异被保留；
- 全 Unknown 与部分 constitution 不会被标为 constituted Relation，也不会进入
  AUTHORIZE/ACTIVATE；
- T5 明确只是 same-process self-configured local fixture assertion；
- G2 line-local envelope 未透传合同和相邻 truth owner 结果；
- 两次运行在新 PID/key/time/nonce 下产生相同 semantic projection。

## 不能支持

- ephemeral self-key 对现实 owner/platform identity 的证明；
- 现实 PKI、pinned trust root、组织 Authority、法律充分性或合法 delegation；
- 跨 run/controller 的持久化 replay 防护；
- 恶意同 OS 用户、本机管理员或可改 controller/worker/profile 者下的强隔离；
- 真实平台 applicability 或真实产品执行；
- current G5 Authority、commit-time policy head、G6 target-native Effect；
- requester/venue Acceptance、O_P Settlement；
- 完整 CE-001 八 case、G1–G7 episode、迁移或恢复；
- 强中心、成熟组合、人工制度、通用模型或新机制的赢家；
- V1/V2 一般解、生产恢复、正式 claim 或机制状态变化。

本轮 G2 runner 增加的 `CE001-E2-ALL-UNKNOWN` 是 line-local diagnostic，不是 CE-001 合同
case 已运行，也不改变 contract、Problem、LineContract 或 MechanismProfile 状态。

## 写入边界

本轮只修改：

- `experiments/wave-012-ce001-power-restoration/g2-relation/`
- `external/codex-cli-cohort-003/G2-fix2-final.md`

未修改 `COMMON.md`、`G2-PROMPT.md`、`G2-FIX-PROMPT.md`、`G2-fix-final.md`、
`ROOT-LIVE-AUDIT.md`、CE-001 contract、`research/NOW.md`、PROGRAM、Problem、
LineContract 或机制状态。
