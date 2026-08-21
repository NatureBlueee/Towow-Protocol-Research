# G4 CE-001 根红灯修复最终记录

日期：2026-07-30  
状态：`LOCAL ROOT REDS CLOSED / 19 TESTS PASS / REAL WORLD NOT_RUN /
NO FORMAL PROMOTION`

## 结论

本轮关闭了根审计指出的两个红灯，并在盲审中继续发现、修复了两个相邻的实际 reliance
缺陷：

1. Effect service 不再生成 Acceptance。Effect 只写 O_E receipt；O_Q 与 O_V 的两个
   `AcceptanceOwnerService` 必须在 exact reconciliation 后分别产生 act。
2. Acceptance closure 不再按 record 数量闭合。required owner 来自冻结的 Q/venue owner
   roles；声明必须恰好为 distinct `{O_Q,O_V}`，acts 也必须由两个唯一 issuer 恰好覆盖。
3. 每个 act 验证 exact
   `episode_id/Q_version/object_id/operation_id/effect_occurrence_id/effect_revision`、
   current owner revision，以及绑定完整 act payload、owner state/service 和 Effect receipt
   的 provenance hash。重复 O_Q 不能代替 O_V。
4. 10-case family 实际包含 Effect 后 O_V 拒绝、wrong episode、wrong Q、wrong Effect、
   stale act、duplicated owner，以及 exact readback 持续 `PENDING` 的
   `Y_resolution=false` case。
5. C 的首轮盲审发现 provenance 未绑定 act bytes，以及过期 reservation/commit evidence
   仍能执行。主会话修复后，C 用原攻击重新复核为 PASS：四种 act tamper 均使 provenance
   false；tick 73 的过期提交为 attempt 1、Effect 0、target delivery 0。
6. matched no-interaction 输出已删除 advantage/delta 解释，只保留
   `LOCAL_STATE_MACHINE_NECESSARY_CONDITION_ONLY`：在当前状态机中，缺少 reservation 与
   current commit evidence 的 submit 不能产生 Effect。

## 实际内部 Agent

- `A / g4_a_truth_boundary`：只读、独立重建 Acceptance/Resolution 真值边界。它明确了
  Effect resolution 与 Acceptance 正交：Effect 已对账但 owner 拒绝或 act invalid 时应为
  `Y_resolution=true, Y_acceptance=false`；真正的 resolution 负例来自 exact effect 状态在
  horizon 内仍非终态。
- `B / g4_b_implementation`：实现独立 owner services、exact closure、10-case fixture、
  worker/broker action、测试与本地文档。B 的冻结版本为 `17/17 PASS`，但没有覆盖随后被 C
  发现的两个缺陷。
- `C / g4_c_blind_audit`：第一阶段不读 tests、README、failure history、根审计或 final，
  先预注册 mutation 预期，再实际攻击。首轮判定 FAIL；主会话整合修复后，C 以原 mutation
  复核 `19/19 PASS`，且 holdout hash 前后不变。

三者共享模型家族、仓库和本机环境；这是职责与执行路径分离，不是外部实验室独立复现。

## 真实分母

### Case/outcome 分母

| 坐标 | 实际结果 |
|---|---:|
| local cases | 10 |
| `Y_success=true` | 8/10 |
| `Y_resolution=true` | 9/10 |
| `Y_effect=true` | 9/10 |
| `Y_acceptance=true` | 2/10 |
| eligible Effect coverage | 9/9 |
| duplicate / unsafe / wrong-object reliance | 0 / 0 / 0 |
| unreconciled Effect | 1/10 |

`Y_success` 为历史兼容坐标，只表示“首次 attempt 产生 Effect”。它不是 CE-001
`ExactTaskSuccess`：owner 拒绝或 Acceptance act invalid 的 case 仍可能
`Y_success=true`，E3B 则因首次 attempt 无 Effect 而为 false，即使 retry 后 Effect 与
Acceptance 均闭合。不得把它映射为完整任务成功。

P1 resolution 不再是 one-class：

```text
truth = 9 true / 1 false
worker prediction = 10 YES
TP=9, FP=1, TN=0, FN=0
false_reliance_conditional=0.1
selective_coverage=1.0
```

这只证明当前固定 worker 在这个 10-case family 上实际产生一个 false reliance；没有 TN/FN，
不能支持类别判别能力或一般 calibration 优势。P1 Acceptance truth 为 `2 true / 8 false`，
worker 全部 abstain，selective coverage 为 0。

### 实际 failure injection

```text
DROP_SUBMIT_ACK@effect                  8
DROP_SUBMIT_ACK@no-effect              1
WRONG_OBJECT_READBACK                  9
CONCURRENT_DOUBLE_DELIVERY             1
REVOKE_AFTER_RESERVATION_BEFORE_COMMIT 1
OWNER_REFUSAL_AFTER_EFFECT             1
ACCEPTANCE_WRONG_EPISODE               1
ACCEPTANCE_WRONG_Q                     1
ACCEPTANCE_WRONG_EFFECT                1
ACCEPTANCE_STALE_REVISION              1
ACCEPTANCE_DUPLICATED_OWNER            1
NONTERMINAL_EXACT_READBACK             1
```

wrong-object 的真实分母是 9，不是 10：revoke case 在 commit 时停止，没有 attempt/readback。

## 保留回归

- E3A：attempt/effect/Acceptance = `1/1/true`；
- E3B：attempt/effect/Acceptance = `2/1/true`，首次 success 仍为 false；
- E3 pair：7 个有限 prefix；pre-attempt 同构，首个区分 witness 仍为 exact
  reconciliation；
- double-submit：target delivery 2、Effect 1、`DuplicateEffect=false`；
- revoke：attempt 0、Effect 0、`UnsafeEffect=false`；
- wrong-object：9 个实际 readback case 的 `WrongObjectReliance=0`；
- Effect-only direct test：Effect 1、Acceptance records 0、O_Q/O_V act count `0/0`；
- 过期凭据 direct test：submit 前 tick 72、提交后 tick 73、Effect 0。

## 失败历史

本轮没有用最终绿灯覆盖以下失败：

1. 原实现由 O_E service 同步生成两条 Acceptance，且 `len(records)==2` 使
   `["O_Q","O_Q"]` 伪闭包。
2. 原 4-case P1 resolution 全 true，`TP=4` 是 one-class。
3. 第二轮首版接口升级后，旧测试真实得到 `9 pass / 1 failure / 1 error`：旧分母仍写
   `3/3`，direct test 又缺新增的 `episode_id`。
4. B 的 `17/17 PASS` 后，C 仍复现 provenance tamper `4/4` 被误判 valid。
5. C 又复现 tick 73 的过期 reservation/commit 提交仍产生 Effect 1，且旧 evaluator 报
   `UnsafeEffect=false`。
6. 主会话修复这两个盲审红灯后，C 用相同攻击复核通过；当前定向回归为 `19/19 PASS`。

更早的 test-first import error、ResourceWarning 和 WrongObjectReliance truth-copy 修复继续
保存在 `g4-reliance/FAILURE_HISTORY.md`。

## 验证

```bash
cd /Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-012-ce001-power-restoration/g4-reliance
PYTHONPYCACHEPREFIX=/tmp/ce001-g4-pycache python3 -m unittest discover -s tests -v
PYTHONPYCACHEPREFIX=/tmp/ce001-g4-pycache python3 runner.py --self-test
PYTHONPYCACHEPREFIX=/tmp/ce001-g4-pycache python3 runner.py --full
PYTHONPYCACHEPREFIX=/tmp/ce001-g4-pycache python3 -m py_compile \
  module.py worker.py runner.py tests/test_g4.py
python3 -m json.tool public_fixture.json >/dev/null
python3 -m json.tool private_holdout.json >/dev/null
```

最终 holdout SHA-256 前后均为：

```text
d9bf6f2346f6bb5cfaba741071fae760e19df41c112ef9986665d6849a249536
```

## 最窄证据边界

当前能支持：

- 本地结构上 O_E Effect 与 O_Q/O_V owner act 已分离；
- exact owner set、tuple、effect occurrence、current revision、expiry 与本地 provenance
  hash 的 closure gate 能拒绝本轮列明的 mutation；
- 当前 10-case deterministic state machine 能复现 ACK-loss、wrong-object、retry、
  duplicate delivery、revoke、Acceptance invalidity 与 nonterminal readback；
- P1 resolution 的固定 worker 结果不再被 one-class 绿灯掩盖。

当前不能支持：

- owner service 位于独立权限域，或本地 hash 等价于外部签名、法律 Authority；
- CE-001 完整 `ExactTaskSuccess`、真实产品能力或任何 arm 优势；
- matched no-interaction 的现实因果效应或 interaction 的方法优势；
- production concurrency/reliability、正式 G4/CE-001 claim promotion或新机制必要性。

```text
REAL_PRODUCT = NOT_RUN
REAL_TEMPORARY_POWER = NOT_RUN
HUMAN_AUTHORITY = NOT_RUN
HUMAN_ACCEPTANCE = NOT_RUN
FORMAL_STATUS_CHANGE = NONE
```

