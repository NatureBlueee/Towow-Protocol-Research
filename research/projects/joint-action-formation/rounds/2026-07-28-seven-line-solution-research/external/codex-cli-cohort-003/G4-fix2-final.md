# G4 第二次根红灯修复最终记录

日期：2026-07-30  
状态：`LOCAL ROOT MUTATIONS CLOSED / B 35 OF 35 / C 8 OF 8 /
INTEGRATION PREFLIGHT 14 OF 14 / REAL WORLD NOT_RUN / NO FORMAL PROMOTION`

## 结论

第三轮不再把同一父进程内的两个 Python 对象、公开可重算 SHA 或 G4 自报的合同字段当成
owner 来源与任务成功。当前实现形成了以下本地闭环：

1. O_E、O_Q、O_V 是三个实际 `Popen` child。每个 child 在自己的进程内生成 Ed25519
   private key，controller 只 pin public key；actual `Popen.pid` 必须等于 child
   `reported_pid`，并与 `process_instance_id/service_id/state_source_id/act_source_id/
   actor executable sha256` 一起进入签名与 trust binding。
2. controller 不再创建 owner Python 对象或读取 owner state。READY、target-native record
   与 owner act 都从 child stdout 的 exact transmitted bytes 解析；公开 payload SHA 只做
   byte integrity，不能产生 Ed25519 signature。
3. O_Q/O_V 的 PID、process instance、service、state source、act source 和 public key 必须
   distinct。同 service id mutation、同 PID/process/state/act source tamper、跨 owner
   signature replay、payload tamper 与不调用 child 的两条 controller-forged act 均不能
   closure。
4. owner request 之前 broker 检查，owner child 收到 request 后再次检查 exact tuple、
   O_E pinned signature/process binding、fresh exact reconciliation、`SUCCEEDED`、C7、
   3kW±5%、至少 45 分钟、无其他线路、deadline、occurrence/revision 与 target payload
   bytes。`PENDING/NO_RECORD/0kW/C8/other circuit/short duration/deadline miss/
   exact_reconciliation=false/wrong O_E signature` 均不得送入 owner act source。
5. G4 最终 envelope 只返回 `P0/I/P1`、attempt、readback、reconciliation、owner-act
   closure、reliance calibration、ACK pair、failure injection、process/source/adapter
   等 line-local evidence。所有 `Y_*`、`ExactTaskSuccess`、`CorrectResolution`、
   `UnsafeEffect`、`DuplicateEffect`、`WrongObjectReliance`、`UnreconciledEffect`、
   `contract_*` 和其他合同级字段已从 runner output 移除。
6. legacy `Venue-V/Circuit-C7` 只能经显式
   `G4_LEGACY_TARGET_V1_TO_CE001_CANONICAL_V1` adapter 对齐
   `VenueV:CircuitC7`；adapter id/version/source/target/mapping hash 任一变化均 fail closed，
   没有字符串替换。
7. E3A/E3B、expiry、revoke、wrong-object、double-submit、owner refusal/wrong tuple/
   stale/duplicate、PENDING resolution negative 与原 19 tests 全部保留。matched twin
   继续只标 `LOCAL_STATE_MACHINE_NECESSARY_CONDITION_ONLY`。

## A/B/C 实际身份与分工

- A `/root/g4_a_scope`：只读重建 G4 有权输出的 line-local 白名单、独立 source/process
  最小设计、19 项保留风险与新增 root mutations；未修改文件。
- B `/root`：实现 `actor_process.py`、process client、双层 pre-act gate、显式 adapter、
  line-local runner、35 项测试、README 与 failure history。
- C `/root/g4_c_attack`：独立本地一致性与负例复验。第一次任务措辞触发平台分类，没有
  产生技术结论；第二次长运行由主会话中断；第三次按最小冻结集合实际运行 `8/8 PASS`，
  用时 17.096s。

A/B/C 共享仓库、本机和模型环境；它们提供职责与执行路径分离，不是外部实验室独立复现。

## B 的真实分母

### 测试

```text
unittest = 35/35 PASS
runtime = 35.376s
runner --self-test = SELF_TEST_PASS
py_compile = PASS
public/private JSON parse = PASS
integration preflight = 14/14 PASS
```

原 19 项风险逐项保留；新增 16 项覆盖：

```text
actual child PID/process/source uniqueness
duplicate signed service id
duplicate/tampered PID, process instance, state source, act source
public digest recompute without child
cross-owner signature replay
PENDING pre-act gate
0kW pre-act gate
wrong C8 pre-act gate
other circuit pre-act gate
short duration pre-act gate
deadline miss pre-act gate
wrong O_E signature
absent exact reconciliation
explicit adapter fail-closed
contract field/preflight passthrough
controller transmitted-byte path
```

### 10-case local holdout

```text
case_count = 10
eligible target-record coverage = 9/9
owner-act closure = 2/10
matched no-interaction target records = 0/9
duplicate target occurrence cases = 0
attempt authorization violation cases = 0
wrong-object without exact followup = 0
target record without terminal reconciliation = 1
```

P1 terminal reconciliation calibration：

```text
TP=9 FP=1 TN=0 FN=0
false_reliance_conditional=0.1
selective_coverage=1.0
```

它只有一个 false-reliance discriminator，仍没有 TN/FN，不支持一般 calibration。

保留的 observed failure injection：

```text
DROP_SUBMIT_ACK@target-record            8
DROP_SUBMIT_ACK@no-record                1
WRONG_OBJECT_READBACK                    9
CONCURRENT_DOUBLE_DELIVERY               1
REVOKE_AFTER_RESERVATION_BEFORE_COMMIT   1
OWNER_REFUSAL_AFTER_TARGET_RECORD        1
OWNER_ACT_WRONG_EPISODE                  1
OWNER_ACT_WRONG_Q                        1
OWNER_ACT_WRONG_OCCURRENCE               1
OWNER_ACT_STALE_REVISION                 1
OWNER_ACT_DUPLICATED_ISSUER              1
NONTERMINAL_EXACT_READBACK               1
```

private holdout SHA-256 在 runner 前后相同：

```text
ff6dcb1efc211ec67d974d3a2d5bcd2d3bfe1ad0d6a3d81010f831d80877911e
```

## C 的独立最小复验

C 实际运行以下 8 个预注册负例：

```text
actual child identity/source distinct
public digest cannot forge owner closure
PENDING request_count == 0
0kW request_count == 0
C8 request_count == 0
wrong O_E bytes request_count == 0
absent exact reconciliation request_count == 0
compact G4 has no contract passthrough and enters qualified preflight
```

结果：

```text
8/8 PASS
exit_code = 0
unittest time = 17.096s
adapter .replace( scan = empty
```

C 没有打印或保存具体 PID 值；它验证的是 equality/distinctness predicate。C 没有独立复验
全部 35 项，也不构成真实 owner/Effect/Acceptance 的外部复现。

## integration output 边界

当前 G4 compact envelope 实际置入 `qualified-e1.json` 的 G4 component 后：

```text
preflight_status = QUALIFIED_COMPONENT_OUTPUTS
rejections = []
contract_score_status = CONTRACT_SCORE_NOT_COMPUTED
```

独立 recursive key scan 对完整 runner output 返回：

```text
forbidden contract-level keys = []
contract_* keys = []
```

这表示 G4 line-local evidence 可以进入 fail-closed preflight，不表示 CE-001 evaluator 已运行。

## 失败历史

本轮保留而不覆盖以下红灯：

1. 第二轮 `19/19 PASS` 后，O_Q/O_V 仍是同一父进程内对象；同 service id 仍可闭合。
2. 第二轮 provenance 只是公开 SHA；controller 不调用 owner `issue_act` 也可构造两条 record。
3. 第二轮 broker 只看“调用过 reconciliation”，使
   `PENDING/0kW/wrong circuit/other circuit` 仍可能请求 owner act。
4. 第二轮 G4 output 含 `Y_effect/Y_acceptance` 等合同字段，已修 preflight 会拒绝。
5. 第二轮 object id 为 `Venue-V/Circuit-C7`，与 integration canonical id 不同。
6. B 第三轮首次运行在 child READY 前真实失败：`python3 -I` 屏蔽本机
   `cryptography`，同时暴露 startup exception 的 process/pipe cleanup 缺口。改为绝对
   actor script、净化环境和异常 force-close 后才得到当前绿灯。
7. C 第一次复核因平台分类失败，不能计入；第二次长运行被中断，不能计入；只有第三次
   `8/8` 是可计入的 C 结果。

## 当前能支持与不能支持

当前能支持：

- 本地 cooperative process model 中 O_E/O_Q/O_V 是实际不同 child；
- actual PID、process instance、service/state/act source、key 与 exact transmitted bytes
  的 current-run pin/signature 可以拒绝本轮列明的重用、重算、tamper 与 replay；
- exact target/reconciliation gate 在发送 owner request 前拒绝列明的 invalid target
  observation；
- 当前 G4 output 是 integration preflight 可接收的 line-local envelope；
- 当前 10-case state machine 继续复现 ACK-loss、expiry、revoke、wrong-object、
  idempotency、owner refusal/mutation 与 nonterminal reconciliation。

当前不能支持：

- hostile same-user OS isolation、现实 owner identity、长期 key custody 或法律 Authority；
- 真实 owner act、现实供电 Effect 或真人 Acceptance；
- 一般 reliance calibration、现实因果优势或任何 arm winner；
- 完整 CE-001 `ExactTaskSuccess`、合同 evaluator、产品运行或正式 claim promotion。

```text
REAL_OWNER_ACT = NOT_RUN
REAL_EFFECT = NOT_ESTABLISHED
REAL_ACCEPTANCE = NOT_ESTABLISHED
GENERAL_CALIBRATION = NOT_ESTABLISHED
COMPLETE_CE001 = NOT_RUN
FORMAL_STATUS_CHANGE = NONE
```

## 复现命令

```bash
cd /Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-012-ce001-power-restoration/g4-reliance
PYTHONPYCACHEPREFIX=/tmp/ce001-g4-fix2-pycache python3 -m unittest discover -s tests -v
PYTHONPYCACHEPREFIX=/tmp/ce001-g4-fix2-pycache python3 runner.py --self-test
PYTHONPYCACHEPREFIX=/tmp/ce001-g4-fix2-pycache python3 runner.py --full
PYTHONPYCACHEPREFIX=/tmp/ce001-g4-fix2-pycache python3 -m py_compile \
  actor_process.py module.py worker.py runner.py tests/test_g4.py
python3 -m json.tool public_fixture.json >/dev/null
python3 -m json.tool private_holdout.json >/dev/null
```
