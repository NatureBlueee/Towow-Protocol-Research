# Codex CLI cohort 003：G6 第二次根红灯修复返回

日期：2026-07-30  
状态：`LOCAL SYNTHETIC FIVE-OWNER CURRENT-RECEIPT/NATIVE-LEDGER COMPONENT /
THIRD-PASS ROOT REDLIGHTS CLOSED / REAL PRODUCT NOT_RUN / NO FORMAL PROMOTION`

## 结论

第二轮的五 process/state shard 与 honest raw-byte RPC 能力保留；第三轮修复了 bytes 离开
`OwnerClient._invoke()` 后 currentness、native truth 与 evaluator closure 三次断链。

现在 G6 method 只能消费当前 `OwnerClient` 在当前 session、当前实际 client process 内，
针对 exact canonical request 实际登记且尚未消费的 response。每个 response 同时绑定
owner/endpoint、request bytes/hash、session、owner instance、实际 owner/client PID、
nonce/ordinal、native state head、native ledger head 与 native record refs。格式正确但没有
当前 native state/ledger 的 payload、跨 session/owner/endpoint/request replay、同 session
旧 response 与 detached decoder 都 fail closed。

最终根会话独立复跑数字：

```text
PRESERVED PRIOR REGRESSION             54/54 PASS
INDEPENDENT AGENT C FIX2 REDLIGHTS     12/12 PASS
IMPLEMENTATION CURRENTNESS TESTS       12/12 PASS
FULL SUITE                             78/78 PASS
SEMANTIC CONFORMANCE                     6/6 PASS
FAILURE INJECTION                        4/4 PASS
LOCAL SYNTHETIC CORRECT RESOLUTION        8/8
G6 LINE-LOCAL CLOSURE                     6/8
RAW OCCURRENCES                             8
WRONG-TARGET REAL EFFECT                    1
RECOVERY                                    1
DUPLICATE EFFECT                            0
CANONICAL OWNER API CALLS                  63
RAW E2E TRACE LINES                        63
FAILURE TRACE LINES                        20
CONTRACT EXACT TASK SUCCESS   NOT_COMPUTED_BY_G6
REAL PRODUCT EXECUTION                NOT_RUN
PRODUCTION EFFECT                     NOT_RUN
HUMAN ACCEPTANCE                      NOT_RUN
PAYMENT FINALITY                      NOT_RUN
COMPLETE CE-001                       NOT_ESTABLISHED
GRADER BLINDNESS                      NOT_ESTABLISHED
```

`6/8 G6 line-local closure` 没有把正确拒绝或恢复后的伤害改写成成功。E5 是有界拒绝；E3B
保留 C8 wrong-target `POWERED@v1` 伤害、native recovery 和后续 C7 Effect，因此两者均是
正确 resolution，但不进入无伤害 line-local closure。

## 实际 A / B / C

本轮实际建立三名内部 Agent：

1. `/root/g6_fix2_a_evidence`
   - 只读重建 response currentness、native ledger/state 与 evaluator receipt closure；
   - 不读取 grader expected resolution 作为判断，不修改文件；
   - 定位 transport、native truth、evaluator 三处断链，给出逐 owner 不变量与 P0/P1
     测试矩阵。
2. `/root/g6_fix2_b_impl`
   - 只修改 `g6-effect/`；
   - 实现 wire V2、current-client consumption、owner-native records、TraceClosure、
     evaluator back-binding、rejected raw transport receipt 与实现侧回归；
   - 运行 tests、runner、compile 并更新本目录说明和 artifacts。
3. `/root/g6_fix2_c_attack`
   - 不读取 `grader-input.json` 或期待 resolution，不与 B 对齐赢家；
   - 只新增 `tests/test_fix2_redlights.py`；
   - 固化 12 个测试方法及 5 个字段篡改 subtests，覆盖 replay、native ledger 空洞、
     recovery 同源旧读回、O_P 错配与 closure 篡改。

三者共享模型家族、仓库与 synthetic truth author。它们增加职责与失败路径分离，不构成
外部 truth author、独立实验室或 hostile implementation 复现。

## 根因与修复

### 1. current request 不再只存在于 `_invoke()` 的瞬时栈

第二轮 response envelope 只绑定 request hash、owner、endpoint 与 owner PID。method 随后
使用 detached decoder 重新读取 bytes；wrapper 可以绕过当前 client registration，返回旧
session 的格式正确 response。

wire V2 的 canonical request/response 现在共同绑定：

```text
owner_id / endpoint
session_id / owner_instance_id
actual owner_process_id / actual client_pid
request_id / exact request_sha256
nonce / ordinal
pre/post native state head
pre/post native ledger head
native record refs
```

`OwnerClient` 在调用时重验当前 `os.getpid()`；PID 不能替代 session/owner instance。
`G6Method` 通过当前 client 的 registration table 消费 response，要求 receipt 属于当前 run
的 sequence cut 且只消费一次。`response_payload()` 与
`verified_acceptance_payload()` 均不再是 detached evidence API。

跨 session、跨 owner、跨 endpoint、跨 request、同 session stale ordinal、PID/session/
nonce/ordinal/head 篡改全部拒绝。

### 2. transport payload 必须对账 worker dispatch 后的 native record

每个 owner worker 先运行自己的真实 dispatcher、修改自己的 state shard，并在 shard 内追加
endpoint-specific native record；之后才形成 state/ledger attestation 与 transmitted
response。

`response_overrides` 仍保留为 failure injection，但只能替换 transmitted payload，不能改写
dispatcher output、native payload hash、native state head、ledger chain 或 native record
refs。payload 与 native output 不同会留下 raw rejected receipt：

```text
verified = false
consumed = false
rejection_reason = RESPONSE_PAYLOAD_NOT_NATIVE_DISPATCH_OUTPUT
```

失败 bytes 因而仍可审计，但不能进入 method evidence 或 evaluator closure。

### 3. O_E Effect 与 recovery 回到 current native state/ledger

O_E 的 `execute/effects/recover/recovery_state/target_state` 均写入或引用 current native
record：

- Effect readback 绑定 exact operation、occurrence、object 与 current occurrence ledger；
- 无 native occurrence/target state、只有 O_E-shaped Effect bytes 时拒绝；
- recovery command 绑定 damaged occurrence；
- recovery event 与 target readback 必须共同满足 object、from/to state、version、
  last-occurrence 与时间关系；
- native C8 仍为 `POWERED@v1` 时，即使同时重放两份漂亮 readback，也不能执行 fallback。

`recovery_state` 与 `target_state` 仍来自同一 O_E，不再称为独立来源。本轮能够支持的是：
二者绑定同一 current native shard、record refs、state head 和 ledger chain。它不是跨故障域
或恶意 owner 下的独立 readback。

### 4. O_Q / O_V Acceptance 对账各自 current act ledger

O_Q 与 O_V 的 Acceptance act 在各自 process/state shard 中生成。native record 绑定：

```text
act_id / owner / actual process
exact Effect id + Effect digest
episode / Q version
current request hash / session / nonce / ordinal
accepted state / observed_at
```

method 仍要求 exact owner set `{O_Q,O_V}`、两个不同 act、两个不同 current process、同一
exact Effect/episode/Q 与 post-effect time。旧 session response 即使字段完全正确，只要当前
O_Q/O_V act ledger 为空就不能 closure。

### 5. O_P obligation/finality 对账 exact Acceptance set 与 native scheme graph

O_P `open_settlement` native record 保存 canonical exact Acceptance-set hash、current Effect、
current request、obligation、scheme、required/reversal phase set；`settlement_state` 再保存
current obligation/effect 请求、native obligation 与 phase-set hash。

finality 由 current O_P native ledger 的 obligation/phase graph重算，而不是采用 response
自报 `FINAL`。当前 ledger 为空、旧 session obligation/finality、wrong Acceptance set、
wrong Effect、wrong scheme/phase、future cut、reversal 或 detached payload 均不能 settle。

### 6. evaluator 只消费冻结 TraceClosure

runner 在 owner session 关闭前冻结：

```text
actual public plan SHA-256
MethodResult SHA-256
ordered verified/rejected receipts
raw request/response bytes
session + five actual owner PIDs
per-owner native ledger final heads/lengths
overall trace head
```

evaluator 显式接收 `trace_closure` 与从 actual public plan 重算的
`expected_plan_sha256`。它重算 raw bytes、request/response hashes、session/PID/
nonce/ordinal、receipt 顺序、per-owner ledger chain、result refs、plan/result back-binding。
缺 closure、detached result、drop、reorder、duplicate、raw-byte tamper 或 plan/result
transplant 一律使 `evidence_closure_valid=false`。

E3A/E3B 故意共享 opaque public plan identity。根补强一度把 public `result.case_id` 强制
等同 private grader case，导致完整套件 `77/78`、八 case resolution 只剩 `6/8`。修复没有
把 E3 private 分支重新泄漏给 method，而是改为校 actual public plan hash；随后原断言保持并
恢复 `78/78` 与 `8/8`。

evaluator 只输出：

```text
g6_line_local_closure
g6_line_local_components
contract_exact_task_success = NOT_COMPUTED_BY_G6
```

不再用 `contract_components` 包装本线 Acceptance/Settlement 局部判断。

## 红灯历史

有效历史分三段：

1. 第三轮开始前，旧 `54/54` 全绿，但不覆盖本轮断链。
2. 实现侧首个完整复现为 `0/7`：跨 session Effect、Acceptance、O_P finality replay，
   无 native occurrence 的 Effect bytes，recovery/readback 同源双伪造和 detached
   evaluator 均为红灯；中间接口未同步造成的异常未计入有效分母。
3. C 在稳定公共接口上的首次有效运行是 `11/12`。唯一红灯为 fresh TraceClosure 自己无法
   通过 verifier：freeze 与 verify 对 receipt 使用不同 canonical projection。保持 C 测试
   不变，统一 projection 后为 `12/12`。

根会话随后增加三个补强方向：actual client PID drift、第二个 detached Acceptance decoder、
actual plan/closure back-binding。E3 opaque identity 暴露一次 `77/78` 回归并按上一节修复。
最终实现侧为 `12/12`，全量为 `78/78`。

## 根会话独立验证

根会话等待 A/B/C 和并发 runner 全部退出后，从稳定目录串行运行：

```bash
PYTHONPYCACHEPREFIX=/tmp/g6-fix2-root-c-pycache \
  python3 -m unittest tests.test_fix2_redlights -v

PYTHONPYCACHEPREFIX=/tmp/g6-fix2-root-final2-full-pycache \
  python3 -m unittest discover -s tests -q

PYTHONPYCACHEPREFIX=/tmp/g6-fix2-root-final2-run-pycache \
  python3 run.py --mode all

PYTHONPYCACHEPREFIX=/tmp/g6-fix2-root-delivery-compile-pycache \
  python3 -m py_compile model.py wire.py owner_process.py owner_api.py \
    scenarios.py method.py evaluator.py run.py tests/test_*.py
```

结果分别为 `12/12`、`78/78`、runner 数字与本页一致、`py_compile` 退出 0。
三个 JSON 均可由 `jq` 解析；`raw-trace.jsonl` 63 行，`failure-trace.jsonl` 20 行。

## 能支持与不能支持

本轮能支持：

- 当前本地 synthetic harness 中五个 owner 是五个实际 `spawn` process/state shard；
- current `OwnerClient`、canonical raw bytes、actual request/session/PID/nonce/ordinal 与
  native record/head chain共同阻断已测 replay/transplant；
- O_E Effect/recovery、O_Q/O_V Acceptance、O_P obligation/finality 都必须回到本 session
  的 current native record；
- frozen TraceClosure 可以拒绝已测 drop/reorder/byte tamper/detached result；
- wrong-target raw damage、recovery 历史、原 54 项风险语义与 G6 line-local 输出均保留。

本轮不能支持：

- hostile 同权限本机进程、恶意 owner worker、容器/硬件隔离或密码学不可篡改；
- grader 对 parent process 的 hostile blindness；grader 仍在同目录，状态为
  `NOT_ESTABLISHED`；
- 真实电路、真实产品、生产 Effect、真人 Acceptance、付款或法律 finality；
- 外部 truth author、第二独立实现或真实成熟产品比较；
- G1–G5 已合法形成 operation、G7 已完成长期 reopen/migration；
- CE-001 完整七线闭合、真实净价值、新机制必要性或任何正式 claim promotion。

真实产品、生产 Effect、真人 Acceptance、付款 finality 均保持 `NOT_RUN`；完整 CE-001
保持 `NOT_ESTABLISHED`。artifacts 中的本次 PID/hash 是运行副产物，不是 immutable
candidate evidence。

## 下一接口

跨线 integration 只能消费本轮的 frozen TraceClosure、current native record refs、raw
occurrence/recovery/Acceptance/O_P graph 与 public plan hash；不能消费 detached response
payload 或单一 `done=true`。集成 evaluator 必须自行重算合同 deadline、连续 45 分钟、
完整 Authority/安全约束、真实 Acceptance、Settlement 与七线谱系。G6 的
`contract_exact_task_success` 继续固定为 `NOT_COMPUTED_BY_G6`。
