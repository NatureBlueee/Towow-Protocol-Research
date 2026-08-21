# CE-001 G4 line-local reliance module

状态：`LOCAL PROCESS-BOUND COMPONENT / 35 TESTS PASS / REAL WORLD NOT_RUN /
NO CONTRACT SCORE`

本目录只产生 G4 有权产生的局部证据：`P0 → read-only interaction → P1 → reservation /
commit evidence → attempt → readback → exact reconciliation → owner act request` 的顺序、
原始 trace、ACK-loss pair、expiry/revoke/idempotency、wrong-object rejection、owner-act
closure 和 reliance calibration。输出 envelope 固定为：

```text
namespace = G4
qualification = QUALIFIED_COMPONENT_OUTPUT
evidence = line-local observations only
```

输出禁止 `Y_success/Y_resolution/Y_effect/Y_acceptance`、`ExactTaskSuccess`、
`CorrectResolution`、`UnsafeEffect`、`DuplicateEffect`、`WrongObjectReliance`、
`UnreconciledEffect`、任何 `contract_*` 或其他合同级结论。integration preflight 实际接收
当前 compact G4 envelope，同时仍返回 `CONTRACT_SCORE_NOT_COMPUTED`。

## 三个实际 actor process

`OwnerTargetService` 不再创建两个 owner Python 对象。第一次出现 target delivery 时实际
启动三个独立 child：

- O_E：生成并签名 target-native record；
- O_Q：维护自己的 revision/state source，只签自己的 owner act；
- O_V：维护另一 revision/state source，只签自己的 owner act。

每个 child 在进程内生成 Ed25519 私钥；controller 只 pin 公钥，不收到私钥。READY 与每次
record/act 的 exact transmitted payload bytes 都签名，并冻结：

```text
actual Popen.pid == child reported_pid
process_instance_id
service_id
state_source_id
act_source_id
public_key
actor executable sha256
```

三个 actor 的上述 identity/source 必须唯一。controller 只从 framed stdout bytes 解析
record/act；公开 SHA-256 只能验证字节完整性，不能替代签名。没有调用 owner child 的两条
伪 act、同 service id、同 PID/process/state/act source、跨 owner signature replay 或 payload
tamper 都不能闭合。

这是 cooperative local process binding：它证明当前 controller 实际消费了当前 child
签名的 bytes，不证明现实 owner identity、法律 Authority、真人 act，也不抵抗可替换本地
可执行文件的恶意同 Unix user。

## owner act 前置 gate

broker 在向 O_Q/O_V 发送任何 owner request 前检查，owner child 收到 request 后再检查一次：

- exact `episode_id/Q_version/object_id/operation_id`；
- O_E pinned process signature 与 exact target payload bytes；
- exact reconciliation 已发生，且 state 为 `SUCCEEDED`；
- occurrence/revision 与 reconciliation 完全相同；
- `CircuitC7`；
- `3kW ±5%`；
- continuous duration 至少 45 分钟；
- `no_other_circuit=true` 且其他线路列表为空；
- target completion 和当前 request 均未越过 deadline。

`PENDING`、`NO_RECORD`、0kW、C8、其他线路有电、时长不足、deadline miss、缺失 exact
reconciliation、wrong/absent O_E signature 在发送 owner request 前即返回
`PRE_ACT_GATE_REJECTED`；O_Q/O_V 的 `request_count` 保持 0。

## 显式 object adapter

G4 legacy native id 与 integration canonical id 不做字符串替换。唯一允许的映射是：

```text
adapter_id: G4_LEGACY_TARGET_V1_TO_CE001_CANONICAL_V1
source: Venue-V/Circuit-C7
target: VenueV:CircuitC7
mapping_sha256: 3f8cdf7895c1b6c84865641a12a7d04ca88b628d7a5636bdd0b58fbf88bcbe8b
```

adapter id/version/source/target/hash 任一改变均 fail closed；后续公开 binding 全部使用
`VenueV:CircuitC7`，target-native record 另保留 native id 与 adapter id。

## 保留的 case 与证据边界

10 个 holdout case 继续保留 E3A/E3B ACK-loss、double-submit、revoke、owner refusal、
wrong episode/Q/occurrence、stale revision、duplicated issuer 和持续 `PENDING`。
E3A/E3B 仍按 passive/active/full-interaction 三种量词比较；matched no-interaction twin
只标：

```text
LOCAL_STATE_MACHINE_NECESSARY_CONDITION_ONLY
```

P1 terminal reconciliation 的当前固定 worker 分母为 `TP=9, FP=1, TN=0, FN=0`。它只复现
一个 false reliance，不建立一般 calibration。owner-act closure 只在 2/10 local cases
闭合；这不是现实 Acceptance。

运行：

```bash
cd /Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-012-ce001-power-restoration/g4-reliance
PYTHONPYCACHEPREFIX=/tmp/ce001-g4-fix2-pycache python3 -m unittest discover -s tests -v
PYTHONPYCACHEPREFIX=/tmp/ce001-g4-fix2-pycache python3 runner.py --self-test
PYTHONPYCACHEPREFIX=/tmp/ce001-g4-fix2-pycache python3 runner.py --full
PYTHONPYCACHEPREFIX=/tmp/ce001-g4-fix2-pycache python3 -m py_compile \
  actor_process.py module.py worker.py runner.py tests/test_g4.py
```

```text
REAL_OWNER_ACT = NOT_RUN
REAL_EFFECT = NOT_ESTABLISHED
REAL_ACCEPTANCE = NOT_ESTABLISHED
GENERAL_CALIBRATION = NOT_ESTABLISHED
COMPLETE_CE001 = NOT_RUN
FORMAL_PROMOTION = NONE
```
