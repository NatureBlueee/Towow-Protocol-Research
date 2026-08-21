# CE-001 / G7：Agent C 第二轮根红灯冻结

日期：2026-07-30  
身份：`/root/g7_c_v2 / G7 INTERNAL AGENT C V2`  
状态：`PRE-B-V2 BASELINE / 17 RED OF 19 / 2 PASS CONTROLS / 0 ERROR`  
作用域：只冻结攻击、保存原始红灯与可执行验收；不设计或实现 B-v2 修复。

## 1. 独立性与读取边界

本轮 Agent C 在 B-v2 尚未启动时完成攻击冻结。完整读取了：

- cohort-003 `COMMON.md`、`G7-PROMPT.md`、`ROOT-LIVE-AUDIT.md`、`G7-final.md`；
- `g7-evolution/README.md`、`C-adversarial-audit.md`；
- integration preflight `README.md`；
- `CE-001-CONTRACT.md`、cohort-002 `ROOT-ADVERSARIAL-AUDIT.md` 与 `SYNTHESIS.md`；
- 当前 baseline 的 `g7evo/*.py`、`runner.py`、fixture 与全部既有 tests。

我没有读取任何 B-v2 设计文档或实现方案。测试断言来自用户冻结的根红灯、CE-001 owner/
runtime/lineage 边界和 integration preflight 的当前输入条件，不来自 B-v2 的预期内部结构。
Agent 数量、Agent 共识与本文件判断都不构成通过证据；以后只能由实际进程、落盘状态、
传输字节、攻击返回和 preflight readback 关闭对应红灯。

## 2. 首轮实际运行

命令：

```bash
PYTHONPYCACHEPREFIX=/tmp/g7c-v2-baseline-pycache \
  python3 -m unittest tests.test_root_redlights_v2 -v
```

实际结果：

```text
Ran 19 tests in 0.027s
FAILED (failures=17)

RED       17
PASS       2
ERROR      0
SKIP       0
exit       1
```

测试文件首跑 SHA-256：

```text
e0b840a8757822e6643bdb136c781fe1fd9027ec5ab8251785a2590237612124
```

机器可读原始记录保存在
[`raw/root-redlights-v2.json`](raw/root-redlights-v2.json)。以后即使 19/19 变绿，也不得
删除或改写这份 `17 RED / 2 PASS / 0 ERROR` baseline。

## 3. 原始红灯

| ID | 冻结攻击 | baseline 直接观察 | 红灯含义 |
|---|---|---|---|
| C2-RED-01 | controller 注入 current/Authority boolean | `EffectTarget.dispatch(... authority_allowed: bool)` 仍存在 | target 没有消费 current receipt set |
| C2-RED-02 | target-native receipt consumption | 没有 transmitted set、consumption event bytes/hash | 记录 hash 不等于 target 实际使用 |
| C2-RED-03 | wrong/stale/tampered receipt 与 set transplant | 没有四类实际 target 拒绝记录 | fail-closed 未被执行证明 |
| C2-RED-04 | 合并 owner | O_Q/O_V/O_P 只是同进程 Python 对象；无独立 PID、state path、act source | 标识分离不等于 owner source 分离 |
| C2-RED-05 | duplicate owner / response transplant | duplicate O_Q 被拒绝；但 O_Q receipt 改写为 O_V 并重算共享 hash 后，O_P 返回 `SETTLED` | response provenance 可伪造 |
| C2-RED-06 | stale/wrong episode/Q/effect owner response | 没有可执行 attack matrix 或 response bytes | copied fields 可继续自证 |
| C2-RED-07 | O_P post-owner finality | 没有 O_P 独立进程返回及其对 exact O_Q/O_V response hashes 的后序绑定 | finality 仍可由同对象图派生 |
| C2-RED-08 | 同进程假迁移 | 没有 source/target PID、durable state path 或 state byte hash | runtime id 字符串不构成迁移 |
| C2-RED-09 | 旧 runtime 假重启 | 只构造新 `EffectTarget` 对象；没有 source termination、target start、old process restart | object recreation 不是 process restart |
| C2-RED-10 | volatile fence | fence 仍是注入 Python object；没有外部 fence-owner PID/state bytes | 无法支持跨进程 old-epoch 拒绝 |
| C2-RED-11 | capsule fixture hash | 只有内存 payload digest；无发送/接收进程及 transmitted bytes preimage | hash 不证明实际传输 |
| C2-RED-12 | bytes provenance | source/target state、history prefix、owner evidence、occurrence 都没有可复算 byte preimage | fixture 常量仍可冒充证据 |
| C2-RED-13 | history rewrite | 没有 original/persisted/candidate prefix bytes 与实际拒绝记录 | boolean prefix flag 不能关闭 history attack |
| C2-RED-14 | 合同字段与同义结论直通 | run result 扫出 35 个 forbidden paths | G7 仍自行生成合同级结论 |
| C2-RED-15 | G7 namespaced envelope | baseline 没有 `G7 / QUALIFIED_COMPONENT_OUTPUT` 产物 | 不能进入集成预检 |
| C2-RED-16 | exact envelope preflight | 没有可把实际 G7 输出替换进 `qualified-e6` 的 envelope | 手写 fixture 不能替真实产物 |
| C2-RED-17 | 证据边界产物 | 没有 line-local `evidence_boundaries` | 本地进程测试可能再次被过度解释 |

最承重的三个直接 false-green 是：

1. controller 仍可用 `authority_allowed=True` 让 target 提交；
2. O_Q response 改成 O_V label 并重算同源 hash，O_P 仍推进；
3. “source/target/old runtime”都没有跨出当前 Python 对象图。

## 4. 两个 PASS 只是保留性控制

### 4.1 原 E4/E6 风险覆盖仍在

`test_existing_e4_e6_risk_boundaries_are_not_weakened` 只确认 baseline 仍有：

- E4 alternative-bound occurrence、append-only history regression；
- E6 occurrence count 1、readback 后禁止 replay、prefix 保留；
- 当前同对象图中的 old-epoch 拒绝。

它不证明 owner 独立、current receipt consumption、跨进程迁移或外部 durable fence。

### 4.2 负边界仍诚实

`test_field_loss_cost_adapter_and_hidden_pair_boundaries_stay_honest` 只确认：

```text
capsule field loss                 fail closed
cold/repeat full lifecycle         NOT_MEASURED_FULL_LIFECYCLE
adapter semantic independence      NOT_ESTABLISHED
hidden pair                        NOT_CONSTRUCTED
safety-liveness frontier           NOT_RUN
```

这些边界必须在修复中保留；不得为追求新测试全绿而改成正向结果。

## 5. 冻结的可执行验收面

新增测试不是要求某个类名或内部架构，而是要求下面的事实能够由产物复算。

### 5.1 Owner source

O_Q、O_V、O_P 各自必须暴露：

```text
distinct process_id
distinct durable state_path + state_bytes_hash
distinct state_source_id / act_source_id
request_bytes_b64 + request_bytes_hash
response_bytes_b64 + response_bytes_hash
```

测试会从实际文件和传输 byte preimage 重算 SHA-256。O_P 必须由自己的 act source 在 exact
O_Q/O_V response hashes 之后返回；把 O_Q response 改成 O_V、重复同一 owner、移植旧 episode、
wrong Q 或 wrong occurrence 时，不得推进。

### 5.2 Target receipt consumption

`EffectTarget.dispatch` 不得再暴露 controller boolean。target 必须接收 current receipt set，
并产生 target-native consumption event bytes/hash。测试要求：

- transmitted set 与 consumed set 精确相等；
- 没有 duplicate receipt；
- wrong、stale、tampered 与 receipt-set transplant 均形成实际 target 拒绝 event；
- event 的 hash 可从输出 bytes 重算。

### 5.3 E6 process/state/fence boundary

测试要求实际可观察：

```text
source process start → durable state write → termination observed
target different process start → different durable state path
old source runtime different process actual restart
external fence owner different process + persisted epoch bytes
old epoch presented → external owner returns REJECTED_OLD_EPOCH
```

source、target、old restart 与 fence owner 的 PID/identity/state evidence 必须互相可区分。
字符串 identity 不够，当前进程中创建三个对象也不够。

### 5.4 Byte lineage 与 history

测试逐项要求 byte preimage：

```text
capsule
source durable state
target durable state
source history prefix
owner evidence
target-native occurrence
old-epoch rejection
```

`source_kind=FIXTURE_CONSTANT` 不能通过。history rewrite 攻击还要保留 original、
persisted、rewritten candidate 三组 bytes：original 与 persisted 相同、candidate 不同，
且 import/restart 实际拒绝 candidate。

### 5.5 G7 输出与 integration preflight

完整 G7 runtime 产物会扫描合同字段和同义 key。当前明确拒绝：

```text
ExactTaskSuccess / task_success
CorrectResolution / resolution_correct
RecoveryToValue / restored_task_value
UnsafeEffect / DuplicateEffect / WrongObjectReliance / UnreconciledEffect
Authority / legal_authority
Effect / world_effect
Acceptance / owner_acceptance
Settlement / payment_settlement
contract_score / contract_success / complete_solution
```

raw bytes、lineage hash、owner response ref、occurrence ref、reopen/migration state 可以保留；
G7 不可把它们升级为合同结论。

实际 `integration_envelope` 必须是：

```text
namespace = G7
qualification = QUALIFIED_COMPONENT_OUTPUT
```

测试把这个实际产物替换进当前 `integration-preflight/fixtures/qualified-e6.json`，再调用当前
`validate_envelope()`；只有返回
`QUALIFIED_COMPONENT_OUTPUTS / CONTRACT_SCORE_NOT_COMPUTED` 才算进入预检。手写一个相似
fixture 不关闭此红灯。

## 6. 这些测试仍不能证明什么

即使未来 19/19 通过，也只能说明：

- 这 17 个冻结 root mutants 被实际关闭或被可复算边界阻断；
- 当前本机的 owner/runtime/fence 子进程与 durable files 确实分开；
- 当前 byte lineage 能被这些测试重算；
- 当前 G7 envelope 通过 structural preflight。

它仍不证明：

```text
真实产品运行                       NOT_RUN
真人 owner                         NOT_RUN
法律权力域                         NOT_RUN
物理世界 occurrence                NOT_RUN
生产 split-brain                   NOT_RUN
跨产品 portability                 NOT_ESTABLISHED
full-lifecycle net value            NOT_ESTABLISHED
完整 CE-001                         NOT_ESTABLISHED
```

本机不同 PID 与 state path 也不是跨组织独立性、恶意同权限进程的密码学隔离或生产分布式
fence 证明。integration preflight 仍只是 fail-closed admission gate，未来独立 evaluator
才有权计算 CE-001 合同成功。

## 7. 测试合同校正

根复核指出首版冻结测试存在一个接口矛盾：严格输出扫描要求 `run_all()` 全树不得包含合同
字段，但三个 legacy 控制又从同一个 `run_all()` 快照读取旧合同字段。2026-07-30 对测试
接口作了唯一校正：

- duplicate-owner / response-transplant 控制直接调用 legacy `run_e6()`；
- E4/E6 旧风险保留控制直接调用 legacy `run_e4()` / `run_e6()`；
- field-loss、成本、adapter 与 hidden-pair 控制分别调用 legacy case 方法，并从冻结
  fixture 读取未构造 pair 的边界；
- `run_all()` 仍作为严格 G7 输出接受全树合同字段与同义字段扫描，没有放宽任何 forbidden
  key，也没有改变 owner、receipt、process、state、fence、bytes、history 或 preflight
  断言。

这次校正不修改 `raw/root-redlights-v2.json` 中的首次
`17 RED / 2 PASS / 0 ERROR` 记录。该 JSON 保存的是校正前首跑事实；校正后的 baseline
复跑数字单独报告，不能覆盖原始历史。

根复核随后发现第二处测试合同问题：若只替换 combined fixture 的 G7 namespace，preflight
仍会把 G6 手写的 `sha256:effect-001 / accept-* / op-finality` 当作 join refs，反向迫使
G7 复制 fixture 常量。第二次校正因此要求：

- G7 migration `lineage_verification.effect_hash` 必须精确等于公开
  `byte_provenance.effect_occurrence.bytes_hash`；
- G7 migration `recovery.acceptance_hashes` 必须精确等于 O_Q/O_V 各自实际
  `response_bytes_hash`；
- G7 migration `recovery.finality_hash` 必须精确等于 O_P 实际 `response_bytes_hash`；
- 四个 `qualified-e6` 手写 digest label 均不得出现在这些 produced refs 中；
- 只有完成上述断言后，测试才在内存中把相同 actual refs 补丁到 G6 occurrence、两份 owner
  response、O_P after-response/finality 绑定，再运行 preflight。

因此当前 preflight 测试检验的是同一次实际 bytes 谱系的跨线 join，而不是 G7 对 hand-written
fixture hash 的迎合。此次校正同样不修改首次红灯 JSON，也不放宽任何攻击断言。
