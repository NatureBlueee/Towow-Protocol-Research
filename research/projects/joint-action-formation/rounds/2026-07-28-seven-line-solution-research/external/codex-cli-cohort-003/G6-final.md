# Codex CLI cohort 003：G6 Effect / Acceptance / Settlement 最终返回

日期：2026-07-30  
状态：`LOCAL SYNTHETIC COMPONENT + LOCAL SYNTHETIC E2E POSITIVE SCOPED /
REAL PRODUCT NOT_RUN / NO FORMAL PROMOTION`

## 结论

本轮已为 CE-001 建立一个可运行的 G6 module。method 从 public plan 开始，只持有细粒度
owner API capability；它必须实际查询 Authority、target-native occurrence、Adoption、
两方 Acceptance、O_P obligation/scheme phase 和 recovery target state，不能读取完整
owner packet、private expected label 或 evaluator truth。

当前最强且有界的结果是：

```text
SEMANTIC_CONFORMANCE                    6/6 PASS
LOCAL_SYNTHETIC_FAILURE_INJECTION       4/4 PASS
LOCAL_SYNTHETIC_E2E_CORRECT_RESOLUTION  8/8
LOCAL_SYNTHETIC_EXACT_TASK_SUCCESS      6/8
AGENT_C_ADVERSARIAL_TESTS              20/20 PASS
FULL_TEST_SUITE                         41/41 PASS
REAL_PRODUCT_EXECUTION                 NOT_RUN
PRODUCTION_EFFECT                      NOT_RUN
HUMAN_ACCEPTANCE                       NOT_RUN
PAYMENT_FINALITY                       NOT_RUN
```

`6/8` 不是漏算：E5 的正确结果是 owner refusal 后无 Effect；E3B 虽恢复了 C8 wrong-target
damage 并用新 operation 完成 C7，但历史已经违反“不得给其他线路送电”，所以不能把它改写
成 `ExactTaskSuccess`。两者都计入 `8/8 CorrectResolution`，不计入成功分母。

这支持本地合成 G6 semantic projection 和 owner/API/target simulator 的局部端到端执行，
不支持 CE-001 的完整 G1–G7 episode 已闭合，也不支持任何真实产品或方法优越性结论。

## 实际内部 Agent

本 CLI 按 `COMMON.md` 实际建立了三名内部 Agent：

1. `/root/g6_agent_a`
   - 独立重建 G6 原始问题与 CE-001 接口；
   - 不读取 Agent B 实现，不修改文件；
   - 提出 `current state / exact-attempt causality / CountsTowardQ` 正交、wrong-target
     damage 不得消失、O_P obligation subgraph 和 owner API 边界。
2. `/root/g6_agent_b`
   - 实现本地 synthetic owner services、target simulator、G6 method、evaluator、runner、
     failure injection 和原生测试；
   - 只写 `g6-effect/`。
3. `/root/g6_agent_c`
   - 不依赖 private expected label，攻击 truth-copy、response transplant、target
     substitution、Authority、domain collapse、Settlement 伪 final、duplicate Effect 和
     recovery 假成功；
   - 新增 `ATTACK.md` 与 `tests/test_attack.py`；
   - 最终独立复跑 attack `20/20`、full suite `41/41`。

Agent 数量不是独立证据。三者仍共享模型家族、仓库和本地 synthetic truth author，不构成
外部实验室复现或 blind holdout。

## 实现与 truth boundary

目录：

`experiments/wave-012-ce001-power-restoration/g6-effect/`

核心文件：

- `model.py`：raw occurrence、episode binding、Authority applicability、causality、
  `CountsTowardQ`、recovery、Adoption、Acceptance 和 Settlement graph；
- `owner_api.py`：method-visible capability surface 与逐调用 receipt；
- `scenarios.py`：八个 private synthetic worlds、owner services 和 target state；
- `method.py`：只消费 public plan 与 `OwnerClient` 的 G6 method；
- `evaluator.py`：运行后、方法外的结果评价；
- `run.py`：semantic、local E2E、failure-injection 三个独立 denominator；
- `tests/`：41 项语义、执行、证据边界和敌对测试；
- `ATTACK.md` / `VALIDATION.md`：红灯演化、修复和证据限制；
- `artifacts/`：三份结果 JSON、70 行 E2E raw API trace、21 行 failure trace。

method 没有导入 scenario、world、fixture 或 `EXPECTED_RESOLUTION`。它逐项调用：

```text
O_Q  episode_status / requester acceptance
O_S  commit-time Authority
O_E  execute / effects / recover / recovery occurrence / target current state
O_V  Adoption / venue acceptance
O_P  obligation / scheme phases / current cut
```

API receipt 只包含该 endpoint 的 request/response、owner、时点、序号与 hash，不包含完整
world snapshot 或预拼 observation vector。这是受信本地 runner 中的数据流隔离，不是抵抗
拥有同目录读取权限的恶意本机进程的安全沙箱。

## 承重语义

### 1. occurrence、binding、Authority、计数和恢复没有折叠

每个 raw occurrence 分别派生：

```text
current_state_matches_q
exact_attempt_causality
authority_covers_actual_object
episode_contribution
CountsTowardQ
recovery
```

pre-existing C7 state 可以满足当前状态谓词，但不能取得当前 attempt 的因果信用。反方向上，
exact attempt 可以真实造成 C8 damage，但 C7 Authority 不覆盖实际 C8，且
`CountsTowardQ=false`；raw occurrence、实际对象和恢复责任仍保留。

### 2. E3A/E3B 的答案不再从 public plan 泄漏

两支在首次交互前向 method 暴露完全相同的 opaque plan：

```text
public case/episode   E3-ACK-LOST-OPAQUE
attempt count         2
operation/actor/target/time shape  identical
```

分叉只来自 owner readback：

- E3A 在首次 readback 找到 exact Effect，停止，不执行 fallback；
- E3B 读到同一次 attempt 造成的 C8 raw Effect，先执行并读回真实 target-state recovery，
  再用第二个 operation 重建 C7；
- E3B resolution 显式写为
  `RECOVERED_WRONG_TARGET_THEN_EXACT_EFFECT_ACCEPTED_SETTLED`，不会用最终成功擦除损害历史。

### 3. Effect、Adoption、Acceptance 分域

O_E 的 Effect 不自动推出 O_V Adoption。Adoption 必须绑定 exact effect、episode、owner
与 Effect 后时点。Acceptance 必须分别覆盖 `{O_Q, O_V}`，并绑定 exact effect、episode、
`Q@v1` 与 post-effect 时点；同一 O_Q response、wrong-version act 或 pre-effect act 都不能
满足两方 Acceptance。Acceptance 未闭合时不会创建 Settlement。

### 4. Settlement 是 O_P obligation subgraph，不是 bool

每项 Settlement 绑定 exact：

```text
effect_id
obligation_id
scheme
required phases
finality horizon
dispute / chargeback / reversal phases
observation cut
```

wrong-effect obligation、wrong-obligation/wrong-scheme phase、未来 phase 和 provider
self-report 都不能建立 current finality。reversal 新增 `REVERSES` edge 并 reopen 对应
obligation，不重写原 payout/phase 历史。

### 5. recovery 必须改变真实 target state

发送 recovery command 或取得字段形状正确的 reversal receipt 都不够。method 还必须：

```text
读回 O_E recovery occurrence
→ 绑定 exact damaged occurrence/object
→ 独立读取 actual target current state
→ 确认状态回到 occurrence.from_state
→ 确认 state readback 不早于 recovery
```

simulator 的 `recover()` 实际修改 `target_states`。伪造 recovery event、但不改变 target
state 的攻击现在保持 `RECOVERY_UNKNOWN`，不能继续闭合。

## 八个 case 的局部结果

| Case | CorrectResolution | ExactTaskSuccess | 关键结果 |
|---|---:|---:|---|
| E0 platform direct | 是 | 是 | synthetic venue-native path 闭合；不强造 relation |
| E1 extant multi-owner | 是 | 是 | 已给定合法 G6 handoff 后闭合 |
| E2 condition formation | 是 | 是 | 只消费已形成的 public plan；不反证 G2–G5 已解决 |
| E3A ACK lost / Effect | 是 | 是 | exact readback 后不重复 Effect |
| E3B ACK lost / wrong target | 是 | 否 | 1 个 C8 raw damage、1 次真实 recovery、再完成 C7 |
| E4 revoke with alternative | 是 | 是 | revoked operation 不执行，合法 alternative 恢复价值 |
| E5 impossible refusal | 是 | 否 | 无 Effect、无 Settlement、保留有界拒绝 |
| E6 migration replay | 是 | 是 | takeover 只 readback，不重复 submit |

运行汇总：

```text
raw occurrences          8
wrong-target real Effect 1
recoveries               1
duplicate Effect         0
owner API calls         70
raw E2E trace lines     70
failure trace lines     21
```

## 红灯历史

绿色原生测试并未直接作为完成依据：

1. 初次运行 18 项测试出现 11 个 error：API receipt 尚不能 canonicalize dataclass owner
   response；修复后原生套件为 19/19。
2. Agent C 首轮 11 项攻击只有 1 项通过、10 项失败；纠正一条过强的 pre-existing 断言后，
   稳定读回为 3/11 通过、8 项真实红灯。
3. 首轮修复关闭了 owner/domain transplant、episode substitution、wrong owner/actor/time
   Authority、零 observation 伪拒绝、Adoption/Acceptance 串域、wrong scheme finality 和
   bogus recovery receipt。
4. 扩大到 20 项攻击后又出现 3 项红灯：wrong-effect obligation、future phase 提前 final、
   同 operation 多 occurrence 漏报 duplicate。
5. 根会话发现 E3A/E3B 的 attempt 数和 case ID泄漏分支；改成同一 opaque method-visible
   plan。
6. 最后一轮发现一次 recovery 假绿：结构合法的 recovery event 没有真实 target mutation
   仍可闭合；增加独立 target-state readback 后关闭。

所有攻击断言均保留并最终通过，没有用改 expected label 或删除反例取得绿灯。完整演化见
`g6-effect/ATTACK.md`。

## 验证

主会话在稳定目录复跑：

```bash
cd research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-012-ce001-power-restoration/g6-effect

PYTHONPYCACHEPREFIX=/tmp/g6-wave012-root-pycache \
  python3 -m unittest discover -s tests -v

PYTHONPYCACHEPREFIX=/tmp/g6-wave012-root-pycache \
  python3 run.py --mode all

PYTHONPYCACHEPREFIX=/tmp/g6-wave012-root-pycache \
  python3 -m py_compile model.py owner_api.py scenarios.py method.py evaluator.py run.py
```

结果为 `41/41 OK`；runner 读回 semantic `6/6`、failure injection `4/4`、E2E
`8/8 CorrectResolution` 与 `6/8 ExactTaskSuccess`。三份 JSON 可解析，raw traces 分别为
70 与 21 行。

## 能支持与不能支持

本轮能支持：

- 在当前 synthetic author 和已测反例中，G6 的 raw reality、episode qualification、
  Authority、causality、计数与 recovery 可以无损分离；
- owner API 按需 observation 能替代免费完整 owner packet；
- wrong-target damage、pre-existing state、ACK loss、revoke/alternative、refusal 和
  migration replay 能在本地 target simulator 中产生不同执行结果；
- Effect、Adoption、两方 Acceptance 与 obligation-specific Settlement 可以分别阻断；
- 当前未观察到必须新增 Effect protocol 才能表达或执行的 residual。

本轮不能支持：

- 真实电路、真人 Principal、生产付款、法律 finality 或现实恢复；
- 平台、强中心、通用模型、成熟 workflow 或人工制度的真实产品比较；
- G1–G5 已经形成合法 public plan，或 G7 已完成长期迁移/重开；
- hostile-process owner isolation、不同 truth author blind holdout 或第二独立实现；
- CE-001 完整七线 solution、跨域一般性、新机制必要性或正式 claim promotion。

没有发现需要擅自改写 CE-001 contract 的缺陷，因此未登记
`CONTRACT_REOPEN_CANDIDATE`。

## 下一接口

根组合运行若要消费本模块，G1–G5 必须只交付 public plan、exact
`episode_id/Q_version/object_id/operation_id` 和 owner capability handles，不能把 owner
truth 或最终 label装进 handoff。G7 应消费本模块的 raw occurrence、operation lineage、
recovery occurrence、target-state readback、Acceptance 与 obligation graph，而不是一个
`done=true`。

要提高证据强度，下一步应让第二实现者只读 public schema 重建 method，并把 owner stores、
private case identity 和 evaluator 放到 worker 无权读取的权限域，再由不同 truth author
重做 E3 hidden pair。真实产品仍需单独安装和运行；当前全部保持 `NOT_RUN`。
