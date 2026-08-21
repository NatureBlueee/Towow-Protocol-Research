# G2 CE-001 根红灯修复 / Agent C 第二轮独立攻击

日期：2026-07-30  
身份：C（不选择方法赢家，只攻击公开 API、输出和可复核证据）  
处置：`1 ROOT RED FOUND / ROOT REPAIRED / 23 OF 23 C RECHECK PASS /
REAL-WORLD CLAIMS NOT_RUN`

## 结论

修复版关闭了 fixture reflection、receipt 摘要冒充签名、exact binding、owner
substitution、缺 policy、refusal/opposition、T5 裸布尔与坏 proof/readback、G5/G6
越权晋升等本轮攻击面；持久化双跑的 250 份 receipt 也可以从 raw bytes、public manifest
和 Ed25519 public key 独立验签。

但五 owner 独立身份仍有一个根红灯：

> controller 会接受五个 owner 复用同一 key/key_id、同一 manifest PID 和同一
> process_instance_id；它只逐 receipt 对照各自 manifest，没有对五个 manifest 做跨 owner
> 唯一性检查，也没有把 worker 自报 PID 与实际 child PID 独立核对。

因此当前默认 worker 的五组随机身份是一个正例，不能升级为“controller 保证五 owner
process/key 独立”。这条红灯不否定其余已通过的局部边界，也不支持任何方法赢家。

## 写入边界

本轮只新增/修改：

- `tests/test_root_fix_adversarial.py`
- `C-FIX-ATTACK.md`

没有修改 `g2_relation.py`、`owner_worker.py`、`platform_worker.py`、fixture、profile、
runner、README 或 outputs。攻击运行只在临时目录生成定向 profile、endpoint manifest
和 adversarial worker，结束后由临时目录清理。

首轮与发现红灯时绑定的实现 SHA-256：

| 文件 | SHA-256 |
|---|---|
| `g2_relation.py` | `4e83047c24ac63af9a4d618b6c75003e4afe1b68f5da3ad6d8058ae5a95db319` |
| `owner_worker.py` | `e685f79cbeb086be055b852b6b27f661712f503c4beac3af96a8a173d42c545a` |
| `platform_worker.py` | `cd598148d15b38bb74b480d0bfe36ee2dcc90aa79ed59a76697c0daff787b3ca` |
| `run.py` | `cfe79890a11c8aaef729384590d6f311b8d24a30fb4a1d872dc940794492889c` |
| `tests/test_root_fix_adversarial.py` | `6531cbec101571d719e2bd9142e45a9ccc858b0aecbf393d194943d6a53cf76e` |

## 实际红绿历史

### 1. 初始独立攻击

命令：

```bash
python3 -m unittest tests.test_root_fix_adversarial -v
```

结果：

```text
Ran 21 tests in 41.333s
OK
```

即：`21 PASS / 0 FAIL / 0 ERROR`。

### 2. 加入主动五 owner 身份复用攻击

保持前 21 项不变，只新增“共享 key/PID/process instance 必须 fail closed”攻击后，原样运行：

```bash
python3 -m unittest tests.test_root_fix_adversarial -v
```

结果：

```text
Ran 22 tests in 65.684s
FAILED (failures=1)
```

即：`21 PASS / 1 FAIL / 0 ERROR`。唯一失败为：

```text
test_reused_pid_process_instance_and_key_are_rejected_not_just_reported
AssertionError: ReceiptVerificationError or ValueError not raised
```

没有删除、跳过或放宽这条测试，也没有修改 core。

### 3. 持久化证据定向复核

在上述红灯之后增加只读 persisted-output 独立复核，并单独运行：

```bash
python3 -m unittest \
  tests.test_root_fix_adversarial.PersistedEvidenceAttacks -v
```

结果：

```text
Ran 1 test in 0.176s
OK
```

它读取但不改写 `outputs/`。当前保存证据的实际数字是：

- 2 次运行；
- 每次 6 个场景；
- 52 个 process manifest；
- 52 个 unique manifest PID；
- 52 个 unique key id；
- 250 份 signed receipt；
- 764 条 raw trace；
- 两次 semantic projection 相等；
- 全部 process exit code 为 0。

该绿灯只证明已保存的默认运行证据内部一致、可独立验签，不会关闭下面的主动 identity
collision 反例。

## 根红灯：跨 owner identity collision 未被拒绝

攻击使用公开 `run_scenario()`，通过临时 endpoint manifest 给五个 owner 启动 worker。
worker 对每个 owner 返回 exact-bound、Ed25519 可验签 receipt，但故意让五个进程共享：

```text
pid = 424242
process_instance_id = REUSED-PROCESS-INSTANCE
key_id = ed25519:REUSED-ACROSS-ALL-OWNERS:10ba682c8ad13513
private/public key = 同一对
```

实际观察：

```json
{
  "accepted_receipts": 26,
  "manifest_count": 5,
  "owners": ["O_P", "O_Q", "O_R", "O_S", "O_V"],
  "process_exit_codes": [0, 0, 0, 0, 0],
  "rejected_receipts": 0,
  "unique_key_ids": ["ed25519:REUSED-ACROSS-ALL-OWNERS:10ba682c8ad13513"],
  "unique_pids": [424242],
  "unique_process_instance_ids": ["REUSED-PROCESS-INSTANCE"]
}
```

这里区分两件事：

1. controller 的确启动了五个 child process；
2. 它没有证明或强制五个 owner 的签名权、manifest process identity 和 PID surface
   相互独立。

第二项是本轮要求的边界。当前 output/process-exit 里的 PID 都来自 worker manifest，
所以 malicious/misconfigured worker 能让保存证据错误地表示 owner process identity。
同一 key 在五 owner 间复用还会直接消除“独立 owner key”所要表达的 authority-domain
差异。

根会话的最小修复方向应是：

- ready 后验证 manifest PID 等于实际 `Popen.pid`；
- 在五 owner 全部 ready 后，对 `pid`、`process_instance_id`、`key_id` 和 public key
  分别执行跨 owner 唯一性 gate；
- collision 必须在任何 owner query 和 RelationVersion 派生前 fail closed；
- 保存 controller-observed child PID，而不是只重复 worker 自报字段；
- 原样复跑该红灯，不要把 collision 仅记录为 warning。

这不是要求抵抗拥有本机任意写权限的攻击者，也不证明真实 owner 已隔离；它只是修复当前
local synthetic process-boundary 声明内部缺失的可判别条件。

## 已通过的攻击面

### Fixture reflection 与 private profile

- controller config 直接携带完整 `owner_profiles` 时被拒绝；
- 五份临时 private profile 各注入唯一 secret sentinel 和 private blob，config、output、
  trace、receipt、manifest 均未反射这些内容；
- 定向只把 O_V `support` 改为 false 后，仅 O_V claimed/authorized/activated 路径变为
  Unknown，其他 owner 不随之改变；
- public manifest 的 `profile_source` 只有 `id` 与 `sha256`，没有 path、cases 或 profile
  内容。

这能支持“默认 controller-visible surface 没有泄漏全量 profile”；不能支持恶意同目录
worker 无法自行读取其他可读文件。

### Receipt 伪造与 exact binding

- 单独伪造 `act_hash` 被拒绝；
- 篡改 signed payload 后同步重算 `raw_bytes_sha256`、`act_hash` 和 `act_id`，摘要全部自洽，
  仍因原 Ed25519 signature 不匹配而被拒绝；
- bit-flip bad signature 被拒绝；
- O_V receipt 配 O_Q manifest/key 的 owner substitution 被拒绝；
- wrong `episode_id`、完整 Q、`object_id`、`purpose`、`relation_revision`、
  `relation_revision_hash`、`relation_version_hash` 均逐项触发 exact binding mismatch。

### Missing policy、refusal 与 opposition

- `MISSING_ALL` 时五 owner 的五轴全部保持 `UNKNOWN*`，且不产生 AUTHORIZE/ACTIVATE；
- O_S refusal 保留为 `REFUSED_BLOCKING`，并停止 O_S downstream；
- O_V blocking opposition 保留 `DO_NOT_SUPPLY_C7`，并停止 O_V downstream；
- O_V nonblocking `BATTERY_ONLY` 同时保留 supporting/opposing provenance，且不错误删除
  后续 owner intent。

### T5 platform-native applicability

- 裸 `platform_direct_applicable=true` 被拒绝；
- 缺 native proof 被拒绝；
- valid proof 后缺 native readback 被拒绝；
- wrong-object readback 被 exact binding gate 拒绝；
- platform receipt 坏签名被拒绝；
- signed receipt source 与 ready manifest source 不一致时被拒绝；
- 正常 proof/readback 只支持 platform-native applicability，`effect_asserted=false`，
  Effect 仍为 `NOT_RUN`。

### G5/G6 与绿色总状态

- `authorized.truth_owner_boundary = G5_UNVERIFIED`；
- `activated.truth_owner_boundary = G6_UNVERIFIED`；
- 所有 authorized state 为 `G5_UNVERIFIED_OWNER_INTENT_ONLY`；
- 所有 activated state 为 `G6_UNVERIFIED_NO_EFFECT`；
- 没有 O_E act，ACTIVATE payload 均为 `effect_asserted=false`；
- 五轴 `global_status` 全为 `NOT_COMPUTED`；
- 顶层没有 `green`、`success`、`relation_valid`、`overall_status` 或 `result`；
- RelationVersion 明示 `NOT_AN_OWNER_ACT / NOT_AUTHORITY / NOT_EFFECT /
  NOT_ACCEPTANCE`。

## 保存 raw bytes、manifest 与双跑证据的边界

定向 persisted-output 测试没有调用模块内 `verify_receipt()` 来代替独立检查，而是逐份：

- base64 解码 raw bytes、signature 与 public key；
- 重算 raw SHA-256；
- 重建 canonical preimage；
- 以 manifest public key 执行 Ed25519 verify；
- 核对 owner、episode、Q、object、source、PID、process instance 和 key；
- 核对 `process-source-manifest.json` 中 controller、runner、worker、fixture source hash；
- 重建 `raw-trace.json` 与两次 rerun 的 trace 拼接；
- 重建 semantic projections 并核对双跑相等。

这能支持当前保存包的内部真实性和复跑一致性，不能把 self-reported identity 转化为独立
authority，也不能支持真人 owner、法律充分性、Effect 或 Acceptance。

## 证据边界

保持：

```text
REAL_OWNER = NOT_RUN
LEGAL_SUFFICIENCY = NOT_RUN
EFFECT = NOT_RUN
ACCEPTANCE = NOT_RUN
REAL_PLATFORM_PRODUCT = NOT_RUN
FULL_CE001_EPISODE = NOT_RUN
METHOD_WINNER = NOT_COMPUTED
```

当前最强结论是：

```text
G2_SIGNED_OWNER_EVIDENCE_COMPONENT = POSITIVE_SCOPED_WITH_ONE_ROOT_RED
CROSS_OWNER_PROCESS_KEY_IDENTITY_GATE = FAIL
CE001_COMPLETE_SOLUTION = NOT_ESTABLISHED
```

## 根会话修复与原样复跑

以上是 C 在 core SHA-256
`4e83047c24ac63af9a4d618b6c75003e4afe1b68f5da3ad6d8058ae5a95db319`
上形成的独立攻击记录，原始红灯不改写。C 返回后，根会话只修改 controller：

- ready manifest 的 PID 必须等于 controller 实际观察到的 `Popen.pid`；
- 五 owner 全部 ready 后，`pid / process_instance_id / key_id / public_key_b64`
  分别必须跨 owner 唯一；
- 启动中途失败或 identity collision 时，已启动的 child 全部关闭，且在任何 owner query
  与 RelationVersion 派生前 fail closed。

修复后 `g2_relation.py` SHA-256 为
`b7e6c1bc91642751bb26ec573582b4823e4d2799a850c121fdafc03a2ea5942e`。
未修改 C 的 collision worker 或断言，实际复跑：

```text
collision 定向测试：1/1 PASS
C 第二轮完整攻击：23/23 PASS
合并测试：46/46 PASS
```

由于 controller source 已改变，第一次 C 全套复跑还正确发现旧 outputs manifest 的
controller hash 已过期；根会话重新执行 `python3 run.py` 后，persisted-evidence 测试恢复
通过。这条中间红灯说明保存包会检测 source 漂移，而不是被静默沿用。

最终双跑仍为 2 × 6 场景、250 份签名 receipt、52 个 process instance、52 个 unique PID、
52 个 unique key id、764 条 trace，`semantic_rerun_equal=true`，52/52 child exit code 为
0。修复后的最强结论覆盖上面的修复前状态：

```text
G2_SIGNED_OWNER_EVIDENCE_COMPONENT = POSITIVE_SCOPED_LOCAL_SYNTHETIC
CROSS_OWNER_PROCESS_KEY_IDENTITY_GATE = ATTACK_RECHECK_PASS
REAL_OWNER = NOT_RUN
LEGAL_SUFFICIENCY = NOT_RUN
EFFECT = NOT_RUN
ACCEPTANCE = NOT_RUN
CE001_COMPLETE_SOLUTION = NOT_ESTABLISHED
```
# G2 fix2 根红灯攻击增量

本轮在原 46 项风险覆盖之外，新增 `tests/test_fix2_bindings.py`。核心攻击与门槛：

- EXPLAIN_BACK request + child 自签 CLAIM response：response-kind allowlist 拒绝；
- canonical request payload/hash、relation schema、endpoint binding、receipt schema、
  episode-specific operation IDs 的替换、重排或缺失：fail closed；
- global request ordinal、per-process issuer ordinal、nonce/query/request-hash replay：
  严格连续且一次性消费；
- stale、future、malformed UTC freshness：fail closed；
- 五 owner 全 Unknown 或任一 constitution 未闭合：只生成 unresolved candidate，
  `relation_established=false`，不发 AUTHORIZE/ACTIVATE；
- owner/platform ephemeral self-key 只能产生 local conformance；T5 只能是
  `LOCAL_FIXTURE_SELF_ASSERTION_VERIFIED`；
- G2 line-local envelope 的 `contract_fields_emitted=[]`，递归不存在 success/green/result、
  Authority、Effect、Acceptance、Settlement truth 字段。

这些检查不建立真实 PKI、owner/platform identity、Authority 或法律充分性，不运行 G5/G6、
真实 Effect/Acceptance/Settlement 或完整 CE-001。
