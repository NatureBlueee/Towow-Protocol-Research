# Codex CLI cohort 003：G6 CE-001 根红灯修复返回

日期：2026-07-30  
状态：`LOCAL SYNTHETIC FIVE-OWNER-PROCESS COMPONENT / ROOT REDLIGHTS CLOSED /
REAL PRODUCT NOT_RUN / NO FORMAL PROMOTION`

## 结论

第一轮 `41/41` 的根红灯已经修复，而且没有通过删除原回归或修改期待 resolution 取绿。

当前 G6 module 的五个 truth owner：

```text
O_S  Authority
O_E  target-native Effect / recovery
O_Q  Q / requester Acceptance
O_V  Adoption / venue Acceptance
O_P  obligation / finality
```

分别运行在五个独立 `spawn` OS process，并只取得自己的 state shard。method 只接收
canonical transmitted response bytes；`OwnerClient` 不再持有 callable、`PrivateWorld`、
owner state 或 admin snapshot pipe。O_Q/O_V Acceptance 是两个独立 process 产生的 exact
act；O_P 在自己的 process 内产生 obligation 与 finality readback；O_E recovery 绑定受损
occurrence，并由 versioned target-native state mutation 与 readback 共同证明。

当前最窄数字：

```text
ROOT RED-LIGHT ATTACKS             13/13 PASS
FULL REGRESSION                    54/54 PASS
PRESERVED FIRST-ROUND TESTS        41/41 PASS
SEMANTIC CONFORMANCE                 6/6 PASS
FAILURE INJECTION                    4/4 PASS
LOCAL SYNTHETIC CORRECT RESOLUTION   8/8
G6 LINE-LOCAL CLOSURE                6/8
RAW OCCURRENCES                        8
WRONG-TARGET REAL EFFECT               1
RECOVERY                                1
DUPLICATE EFFECT                        0
CANONICAL OWNER API CALLS              63
CONTRACT EXACT TASK SUCCESS             NOT_COMPUTED_BY_G6
REAL PRODUCT EXECUTION                  NOT_RUN
PRODUCTION EFFECT                       NOT_RUN
HUMAN ACCEPTANCE                        NOT_RUN
PAYMENT FINALITY                        NOT_RUN
```

`6/8 G6 line-local closure` 中，E5 是正确的有界拒绝；E3B 保留 C8 wrong-target damage、
完成真实本地恢复后再构成 C7 Effect。两者都是正确 resolution，但不被改写为无伤害的
line-local closure。

## 实际 A / B / C

本轮实际建立了三名内部 Agent：

1. `/root/g6_a_truth_domains`
   - 只读重建 Effect / Acceptance / Settlement truth domains；
   - 独立复现 shared-world closure、非 bytes response、共享 grader 和合同成功名过度；
   - 给出五 owner process/state、Acceptance act、O_P finality 和 recovery CAS/readback
     不变量。
2. `/root/g6_b_implementation`
   - 实现五 process/state shard、canonical bytes RPC、冻结 grader、line-local evaluator；
   - 迁移并保留原 41 个测试函数和反例语义；
   - 只修改 `g6-effect/`。
3. `/root/g6_c_blind_attack`
   - 不依赖期待 resolution，新增 13 项根红灯攻击；
   - 尝试 response transplant、closure/reflection、重复 Acceptance、伪 O_P finality 和
     recovery event + readback 双伪造；
   - 只新增 `tests/test_root_redlights.py`，不修改实现或 grader。

三者共享模型家族、仓库和 synthetic truth author，增加的是失败路径与职责隔离，不构成三次
外部独立复现。

## 根因与修复

### 1. shared `PrivateWorld` 与 closure oracle

第一轮 `make_owner_client(world)` 的 dispatch callable 直接捕获单一 `PrivateWorld`。通过
Python reflection 可以从 `OwnerClient` 对象图恢复完整 world；五个 owner 只是 endpoint
标签，不是独立 truth domain。

第二轮移除了 `PrivateWorld` 和 callable client。`OwnerSession` 以 `spawn` 启动五个
process；每个 worker 初始化时只收到自己的 state shard。method-visible client 只持五条
public RPC connection 和对应 PID，admin snapshot connection 只留在 runner。

### 2. method 实际消费对象，而不是 transmitted bytes

第一轮 method 直接取得 dataclass/list，对 receipt 的 JSON 转换只是事后记录。

第二轮所有 request/response 都是 canonical JSON bytes。response envelope 绑定 owner、
endpoint、exact request SHA-256 和 process PID；trace 同时保留实际 request/response bytes
及双向 hash。跨 owner、跨 endpoint、跨 request 的 response transplant 会在 decode 前被
拒绝。

### 3. Acceptance 与 process provenance

O_Q 与 O_V 各自在自己的 process ledger 产生唯一 `act_id`，act 绑定 exact Effect、
episode、Q version、post-effect time 和 process provenance。Gate 要求 exact owner set
`{O_Q,O_V}`、两个不同 act、两个不同已验证 process。

C 的 13 项首跑为 `12/13`，发现 payload 可以声称两个虚构 PID；两个 channel 虽然真实独立，
method 却没有把 payload PID 与 response envelope PID 相等校验。这一红灯通过
`verified_acceptance_payload()` 关闭：MethodResult 与传给 O_P 的 provenance 只采用已验证
transport PID。测试保持不变后为 `13/13`。

### 4. O_P obligation / finality

O_P 不再与 Acceptance/Effect simulator共享 state，也不由 method 用任意 phase 自行宣布
finality。O_P process 接收两个已验证 Acceptance act，独立建立 obligation 和 scheme state，
再通过 `settlement_state` 返回 finality readback。method 重算本地 phase graph只用于核对
O_P 返回；wrong effect/obligation/scheme、future cut、非 O_P issuer、reversal 与伪 `FINAL`
均不能闭合。

### 5. damaged occurrence recovery

O_E 只允许对其本地 ledger 中 `damage=true` 的 occurrence 执行 recovery。恢复要求：

```text
damaged occurrence id + object + post-damage version
→ target-native state mutation
→ recovery occurrence with higher version and exact reverse binding
→ independent target-state readback
→ state/version/last-occurrence/time all match
```

C 同时伪造 recovery event 与 readback、但不改变 native store 的反例返回
`RECOVERY_UNKNOWN`；C8 仍是 `POWERED@v1`，fallback 不执行，damage 历史不删除。

### 6. grader 与成功主张

`EXPECTED_RESOLUTION` 已从 evaluator module 移除。独立冻结输入为
`g6-effect/grader-input.json`，SHA-256：

```text
7b0b6e2f5162b6d0f69e9e689bf6ebedcc7876372edd892aec1630638f9b8860
```

owner process 与 method 不加载 grader。hash 不匹配时 evaluator 拒绝评分。

G6 的点状 Effect/Acceptance/Settlement 不能独立证明合同中的 `T0+90min` deadline、连续
45 分钟 operation、噪声与完整安全约束，也不能替 G1–G5 证明上游 formation。因此旧
`exact_task_success` 已改为 `g6_line_local_closure`，并显式输出：

```text
contract_exact_task_success = NOT_COMPUTED_BY_G6
deadline = UNKNOWN
continuous_duration = UNKNOWN
full_safety_constraints = UNKNOWN
```

合同级 `ExactTaskSuccess` 留给集成 evaluator 在完整跨线证据上重算。

## 验证

根会话在稳定目录独立运行：

```bash
PYTHONPYCACHEPREFIX=/tmp/g6-ce001-direct-pycache \
  python3 -m unittest discover -s tests -q

PYTHONPYCACHEPREFIX=/tmp/g6-ce001-run-pycache \
  python3 run.py --mode all

PYTHONPYCACHEPREFIX=/tmp/g6-ce001-compile-pycache \
  python3 -m py_compile model.py wire.py owner_process.py owner_api.py \
    scenarios.py method.py evaluator.py run.py tests/test_*.py
```

结果为 `54/54 OK`、runner 数字与本页一致、py_compile 通过。Agent C 另以不改测试的方式
独立复跑 `13/13` 与 `54/54`。它还在同一 harness 中确认五个 owner child 关闭后均
`is_alive=false`、exit code 为 0；系统级 `ps/pgrep` 被 sandbox 拒绝，因此不能扩大成全机
进程表核验。

## 能支持与不能支持

本轮能支持：

- 在当前本地 synthetic harness 中，五个 owner 使用独立 process/state shard；
- method 只消费 owner RPC 实际 transmitted bytes，已测 closure/reflection 与 transplant
  路径不能读取或替换 owner truth；
- O_Q/O_V exact Acceptance、O_P obligation/finality、wrong-target harm 与 versioned
  recovery 可以分别阻断；
- 原 41 个回归和新增 13 个根红灯攻击同时通过。

本轮不能支持：

- hostile OS/container 隔离或恶意同权限本机进程下的机密性；
- 真实电路、真实产品、生产 Effect、真人 Acceptance、付款或法律 finality；
- 不同 truth author blind holdout、第二独立实现或现有产品比较；
- G1–G5 已形成合法 operation，G7 已完成长期 reopen/migration；
- CE-001 完整七线闭合、新机制必要性或正式 claim promotion。

真实产品、生产 Effect、真人 Acceptance 与付款 finality 均保持 `NOT_RUN`。
