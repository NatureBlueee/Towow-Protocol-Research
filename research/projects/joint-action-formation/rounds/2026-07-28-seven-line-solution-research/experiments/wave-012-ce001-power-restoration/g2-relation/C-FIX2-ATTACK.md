# G2 fix2：C 独立攻击复核

日期：2026-07-30  
状态：`ONE PROVENANCE RED FOUND / ROOT REPAIRED / 67 OF 67 FULL SUITE PASS /
NOT INTEGRATION QUALIFIED`

## 独立边界

C 未读取或询问 A/B 对话，不选择期待赢家，只攻击公开 request/receipt、scenario output 与
line-local envelope。未修改生产实现，未运行 `run.py`，未生成或改写 `outputs/`。

复核时生产源快照：

| 文件 | SHA-256 |
|---|---|
| `g2_relation.py` | `40f63494376952cf95ed22e1ea442d55a39ffab757dabfa3d88fb809e1a99228` |
| `owner_worker.py` | `6ed3931303e60f21b0647cf18df766b153d3ed4cf879e5a945b0115791f7eb20` |
| `platform_worker.py` | `03b3674d9eff76ab82d3a4dfd5380e740612929e562eb59f317dd65b0a58092f` |

新增独立测试：`tests/test_fix2_independent.py`。

## 数字

定向运行：

```text
python3 -W error::ResourceWarning -m unittest tests.test_fix2_independent -v
13 tests = 12 PASS + 1 FAIL
```

完整运行：

```text
python3 -W error::ResourceWarning -m unittest discover -s tests -v
67 tests = 66 PASS + 1 FAIL
```

唯一失败是同一个不放宽红灯：

```text
test_private_column_unknown_is_verified_owner_unknown_not_controller_fill
```

## 红灯：PRIVATE_COLUMN_UNKNOWN 被拒后由 controller 占位

`owner_worker.py` 在缺 owner policy 时实际生成并签名：

```text
kind = PRIVATE_COLUMN_UNKNOWN
decision = UNKNOWN
payload.column_state = UNKNOWN
```

但 `OWNER_RESPONSE_KINDS["PRIVATE_COLUMN"]` 只允许
`ABSENT / WITHHELD / DISCLOSED`。因此 exact self-signed Unknown receipt 被
`response kind is not allowed for requested kind` 拒绝；`run_e2` 随后自行写入：

```text
private_column_evidence.state = UNKNOWN
private_column_evidence.verified_act_hash = REJECTED
```

这没有错误打开 RelationVersion 或 downstream gate；all-Unknown 场景仍是
`DERIVED_CANDIDATE_WITH_UNRESOLVED_CONSTITUTION`。但它丢失了一个承重区别：

```text
owner 已签名 UNKNOWN
!=
receipt 无效后 controller 推断 UNKNOWN
```

所以当前不能声称 private-column Unknown 被 owner-native、可验签地保真。按任务要求保留
失败测试，不由 C 修改生产代码。

## 当前通过的攻击

- self-signed wrong-kind response 被拒；
- request payload hash、raw request bytes/hash、operation IDs、request/receipt schema、
  global/process/issuer ordinal 替换被拒；
- stale、future-issued、超长 freshness window、窗口外 signed-at 被拒；
- 同一 verification state 内 query/nonce/request-hash replay 被拒；
- all Unknown 与部分 constitution 都不会建立 RelationVersion，也不会发出
  AUTHORIZE/ACTIVATE；
- raw Ed25519 bytes/signature 独立复验通过，五 owner PID/key/public key 仍唯一；
- refusal、blocking opposition 保留并阻断对应 downstream；
- authorized/activated 仍分别标为 `G5_UNVERIFIED_OWNER_INTENT_ONLY` 与
  `G6_UNVERIFIED_NO_EFFECT`，O_E 仍 `NOT_RUN`；
- T5 proof/readback 被确认来自同一 self-configured platform process，输出将其标为
  `LOCAL_FIXTURE_SELF_ASSERTION_VERIFIED`，同时明确
  `real_platform_identity/applicability = NOT_ESTABLISHED`；
- 对 config 注入和递归 envelope key 扫描未发现合同结果向量、`contract_*` 声明、
  Authority、Effect、Acceptance 或 Settlement 进入 `g2_line_local_envelope`。

## 仍不能支持

- 跨 run、跨 controller 或持久化 replay registry：`UNKNOWN / NOT TESTED`；
- 恶意同 OS 用户或可改 controller/worker/profile 的进程隔离；
- ephemeral self-key 对现实 owner/platform identity、Authority 或法律充分性的证明；
- 真实平台 applicability、Effect、Acceptance、Settlement 或完整 CE-001；
- line-local envelope 之外的 downstream consumer 不误读 raw owner intent；
- 强中心、成熟组合、人工制度、通用模型或新机制的胜负。

因此当前最窄结论是：

```text
REQUEST_RESPONSE_EXACT_BINDING = POSITIVE_SCOPED_LOCAL_SYNTHETIC
IN_RUN_FRESHNESS_AND_REPLAY_GATE = POSITIVE_SCOPED
ALL_UNKNOWN_RELATION_GATE = FAIL_CLOSED
PRIVATE_COLUMN_UNKNOWN_PROVENANCE = FAIL
PLATFORM_TRUTH = SAME_PROCESS_SELF_CONFIGURED_LOCAL_ASSERTION_ONLY
G2_LINE_LOCAL_CONTRACT_TRUTH_PASSTHROUGH = NOT_OBSERVED_IN_ATTACKED_OUTPUTS
G5/G6/REAL_OWNER/REAL_PLATFORM/CE001_COMPLETE_SOLUTION = NOT_ESTABLISHED
```

## 根会话最小修复与原样复跑

C 返回后，根会话没有修改 C 的测试或放宽断言，只把
`PRIVATE_COLUMN_UNKNOWN` 加入 `PRIVATE_COLUMN` response-kind allowlist。这样 O_R 的 exact
signed Unknown receipt 进入 verified owner evidence，且不改变 constitution closure：

```text
private_column_evidence.state = UNKNOWN
private_column_evidence.verified_act_hash = <signed O_R act hash>
relation evidence_status = DERIVED_CANDIDATE_WITH_UNRESOLVED_CONSTITUTION
relation_established = false
downstream_relation_gate_open = false
AUTHORIZE / ACTIVATE acts = 0
```

原样复跑：

```text
C fix2 定向测试 = 13/13 PASS
合并测试 = 67/67 PASS
```

因此红灯后的当前结论覆盖前述失败状态：

```text
PRIVATE_COLUMN_UNKNOWN_PROVENANCE = VERIFIED_LOCAL_EPHEMERAL_OWNER_UNKNOWN
REQUEST_RESPONSE_EXACT_BINDING = POSITIVE_SCOPED_LOCAL_SYNTHETIC
ALL_UNKNOWN_RELATION_GATE = FAIL_CLOSED
PLATFORM_TRUTH = SAME_PROCESS_SELF_CONFIGURED_LOCAL_ASSERTION_ONLY
G5/G6/REAL_OWNER/REAL_PLATFORM/CE001_COMPLETE_SOLUTION = NOT_ESTABLISHED
```
