# G7 第二轮 Agent B 实现记录

日期：2026-07-30  
身份：`G7_INTERNAL_AGENT_B_V2`  
公开输出：`EvolutionModule.run_all()`  
状态：`LOCAL PROCESS/STATE-SEPARATED COMPONENT EVIDENCE`

## 结论

本轮把首轮同一 Python 对象图中的 owner、target gate 和 E6 migration 改成实际子进程、
独立 durable file 与原始传输 bytes。公开 `run_all()` 只返回 G7 line-local evidence 和
`G7 / QUALIFIED_COMPONENT_OUTPUT` envelope；首轮合同形状仅留在
`run_e4()`、`run_e6()`、`run_capsule_field_loss()` 与 `run_regressions()` 内供原 33 项
风险回归，不进入 `runner.py` 的输出。

当前实际原始运行在 [`raw/run-traces.json`](raw/run-traces.json)，窄摘要在
[`results.json`](results.json)。每次 runner 会建立新的 run root，因此 PID、UUID、inode、
state path 和所有 bytes-derived hash 都会变化，不能把本文件中的某次值当 fixture。

## 实际边界

### Owner

`O_Q`、`O_V`、`O_P` 分别由 `python3 -m g7evo.boundary --worker` 的独立 OS process 执行，
各自创建：

- 独立 runtime/start token 与 PID；
- 独立 state file、store UUID、state boundary、state source；
- 独立 act source 与本地 trust-anchor identity；
- request/response 原始 frame bytes、transport hash 与 byte length。

`O_Q`/`O_V` 的请求带完整 episode/Q/object/operation/target、challenge、current head 和
target-native occurrence bytes。`O_P` 收到两份完整 response frames 后，逐项检查 distinct
owner、act source、trust anchor、current head、expiry、exact binding 与 occurrence hash，
再从自己的 state source 作出后序 act。

实际 worker 攻击矩阵包括：

```text
duplicate_owner
response_transplant
stale_response
wrong_episode
wrong_q
wrong_object
wrong_operation
wrong_target
wrong_effect_occurrence
```

九项都产生独立 O_P worker request/response/state readback，`accepted=false`、
`finalized=false`、`state_act_count=0`、worker exit `0`。这不是汇总层预写的拒绝字符串。

### Target-native current receipt consumption

`EffectTarget.dispatch()` 已删除 `authority_allowed` 参数，只接受
`current_receipt_set`；传 controller boolean 会得到 Python `TypeError`，不会触发 transition。
公开 process path 不调用 legacy `owner_signature` 或 `issue_current_receipt_set`。O_R 与 O_S
各由独立 receipt-issuer process 生成并持久化 Ed25519 私钥、state source 与 act source，
只把公钥 trust manifest 和实际 receipt frame 传给 target；两者 PID、state path/source、
act source 均不同，也不同于 target PID。实际 target gate worker 从收到的完整 receipt
frames 验 owner set、Ed25519 signature、固定 public trust manifest、transport/content hash、
exact binding、current head 和 expiry，先把 consumption event 与 state fsync 落盘，再决定
transition。

实际攻击包括：

```text
wrong_receipt
stale_receipt
tampered_receipt
receipt_set_transplant
missing_receipt
duplicate_receipt
wrong_current_head
```

七项都有独立 target PID、event bytes、state path/hash，实际 readback
`target_transition_count=0`。

### E6 process/state/fence

时序是：

```text
source worker 写 source state/history/capsule 后 exit=0
→ target worker 收到 exact capsule bytes 并写不同 state/history path
→ 独立 fence-owner worker 把 epoch 8 fsync 到第三 state path
→ old-source worker 从原 source state 以同 runtime_id、epoch 7、新 PID 实际重启并发请求
→ replacement fence-owner worker 从 durable fence state 恢复 epoch 8
→ 返回 REJECTED_OLD_EPOCH，transition_count=0
```

source/target 的 runtime、PID、state boundary 与 state file 均不同。fence install PID 与
fence readback/rejection PID 也不同，后者只从 fence durable bytes 恢复 epoch，因而没有把
fence 可用性依赖于 source/target coordinator 对象存活。

capsule 带 source runtime seal。target 对 exact received frame、source state bytes、
history prefix bytes、schema、required fields、epoch 与 seal 逐项验证。history candidate
rewrite 和 owner-evidence field loss 均由真实 target-import worker 拒绝；field loss 不被
表述成 portability 成功。

## Bytes provenance

公开 evidence 为下列事实保存 base64 preimage、SHA-256 与 durable readback：

```text
capsule producer/consumer frame
source state
target state
source/target history prefix
O_Q/O_V/O_P owner response manifest
target-native occurrence
target-native receipt-consumption event
external fence state
old-restart request
old-epoch rejection response
```

target history 前 N bytes 与 source transmitted history prefix 做 byte-for-byte 比较，之后
只追加 takeover record。candidate rewrite 使用不同 bytes，通过 source seal/import 验证
实际拒绝，不使用常量 true。

这里的 seal 和 local trust anchor只覆盖受信 harness 下的普通误改、字段移植与流水线替换；
它不抵抗拥有同一用户目录写权限并能读取源码/状态的恶意本机进程。

## 公开输出与 preflight

公开输出严格分层：

- `run_all()`：G7 line-local process/state/lineage evidence；
- `integration_envelope`：只含 G7 reopen/migration/lineage fragment；
- `run_regressions()`：仅供首轮内部测试，不能发布或拼入 integration。

当前 preflight 强制的 `effect_hash`、`acceptance_hashes`、`finality_hash` 分别直接引用
本轮 target-native occurrence raw bytes、O_Q/O_V response raw frames 与 O_P response raw
frame 的实际 SHA-256。integration composition test 会把 G6 的对应引用在内存中对齐到同一组
actual hashes 后再运行 preflight；实现不复制 `qualified-e6.json` 的 fixture 常量。G7
不生成这些上游对象、不计算成功，也不把 digest references 升级为自己的语义。

把 runner 真实产生的 `integration_envelope` 替换进当前 `qualified-e6.json` 后，实际结果：

```text
preflight_status       QUALIFIED_COMPONENT_OUTPUTS
contract_score_status  CONTRACT_SCORE_NOT_COMPUTED
rejections             []
```

## 验证

```text
py_compile                         PASS
原首轮风险测试                    33/33 PASS
第二轮冻结根红灯                  19/19 PASS
新增 process-boundary tests        6/6 PASS
全套                               58/58 PASS
old-runtime commit negative control RED_DETECTED (expected exit 1)
integration-preflight composition  QUALIFIED_COMPONENT_OUTPUTS
```

`raw/root-redlights-v2.json` 的 `17 RED / 2 PASS` 原始红灯没有修改。

## 仍未建立

```text
real product                       NOT_RUN
real human owner                   NOT_RUN
legal power domain                 NOT_ESTABLISHED
physical-world occurrence          NOT_RUN
production split-brain             NOT_RUN
cross-product portability          NOT_ESTABLISHED
second-adapter semantic independence NOT_ESTABLISHED
cold/reuse full-lifecycle net value NOT_MEASURED
hidden safety-liveness pair        NOT_CONSTRUCTED
safety-liveness frontier           NOT_RUN
full CE-001                        NOT_ESTABLISHED
```

E4 alternative recovery、E6 occurrence/owner-act gap、append-only、exact occurrence
reconciliation 与 capsule field-loss fail closed 继续由 internal regression surface 保留。
