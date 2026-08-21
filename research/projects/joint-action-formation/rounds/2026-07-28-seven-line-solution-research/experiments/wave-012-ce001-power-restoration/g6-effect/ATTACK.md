# Agent C 敌对审查：CE-001 G6

## 第三轮 response currentness 攻击（2026-07-30）

第三轮独立 C 固化 `tests/test_fix2_redlights.py` 的 12 项不变量，不读取 grader expected
resolution。攻击覆盖：

- response/request 的 session、owner instance、actual owner/client PID、nonce、ordinal、
  request hash 和 native state/ledger heads；
- cross owner/endpoint/request、same-session stale ordinal 与跨 session replay；
- 无 current O_E native occurrence/state 的格式正确 Effect bytes；
- O_Q/O_V ledger 为空时重放 Acceptance；
- O_P ledger 为空或 Acceptance set/scheme/phase 错配时重放 finality；
- 同源 recovery_state/target_state replay 掩盖实际 C8 `POWERED@v1`；
- detached response decoder；
- TraceClosure drop、reorder、raw byte tamper 和 detached result。

首个公共接口运行 `11/12 PASS`，唯一红灯是 fresh TraceClosure 的 freeze/verifier canonical
receipt projection 不一致。修复保持 C 断言不变后为 `12/12 PASS`。实现侧另从 `0/7`
复现扩展到 `12/12 PASS`，全量旧回归与新增攻击合计 `78/78 PASS`；新增门覆盖 actual
client PID drift、第二个 detached Acceptance decoder 和 plan/closure transplant。

本轮把 rejection 与 evidence 分开：native mismatch response 仍以 raw transport receipt
留痕，但标记 `verified=false / consumed=false`，不能进入 evaluator closure。O_E recovery
的两次 read 仍来自同一 owner；保证来自 current native shard 与 ledger seal，而非来源独立性。

> 第二轮根红灯修复说明（2026-07-30）：下文是第一轮 41 项回归的历史审查记录，不再证明
> 当前 owner isolation。当前实现已移除捕获单一 `PrivateWorld` 的 callable closure，改为
> 五个 `spawn` owner process、canonical response bytes、独立 O_Q/O_V Acceptance act、
> O_P obligation/finality readback、冻结 grader hash 与 versioned target-native recovery。
> 原 41 个测试函数及其反例语义均保留并迁移；当前合同级
> `ExactTaskSuccess` 不由 G6 计算，只保留 `g6_line_local_closure`。

## 第二轮根红灯攻击（当前）

第二轮 Agent C 为 `/root/g6_c_blind_attack`。它不知道冻结 grader 的期待 resolution，只从
owner isolation 与证据完整性不变量建立 `tests/test_root_redlights.py` 的 13 项攻击：

- 五个 owner 的 PID 与 state shard 必须唯一，且不等于 method/evaluator PID；
- `OwnerClient` 对象图与 callable closure 不得到达 world、owner state 或 grader；
- owner RPC 只返回 canonical response bytes；
- O_Q response bytes 移植到 O_V endpoint 必须拒绝；
- 重复 `act_id`、重复 process 或 payload 伪造 process provenance 必须阻断 Acceptance；
- 非 O_P obligation、伪 O_P finality 与 reversal 冲突不能结算；
- recovery event 与 readback 同时伪造、但 native state 未变时必须保持
  `RECOVERY_UNKNOWN`；
- owner payload 不得包含 grader truth；
- G6 不得输出合同级 `ExactTaskSuccess` 布尔值。

首次运行是 `12/13 PASS`。唯一红灯是 Acceptance payload 可以声称两个不同的虚构 PID，
从而绕过“两个不同 process”检查。实现没有改期待答案，而是把 payload provenance 绑定到
已验证 response envelope 的 transport PID。保持原测试不变后的结果为：

```text
root red-light attacks       13/13 PASS
full regression              54/54 PASS
preserved first-round tests  41/41 PASS
```

Agent C 独立关闭一组五 owner 后，五个 child 均 `is_alive=false`、exit code 为 0。该结果只
证明当前本地 synthetic harness 的 process/wire/state-shard 边界，不证明 hostile OS/container
隔离或真实主体独立性。

日期：2026-07-30  
第一轮身份：`/root/g6_agent_c`（内部 Agent C）  
第一轮历史处置：`20/20 ATTACK PASS / 41/41 FULL SUITE PASS / LOCAL SYNTHETIC ONLY`

## 审查边界

本审查完整读取根 `AGENTS.md`、cohort-003 `COMMON.md`、`CE-001-CONTRACT.md`、
cohort-002 `ROOT-ADVERSARIAL-AUDIT.md` 与 `SYNTHESIS.md`。我没有读取 private expected
label；攻击断言不依赖 evaluator 的 `EXPECTED_RESOLUTION`。

Agent C 只新增或维护：

- `ATTACK.md`
- `tests/test_attack.py`

没有修改 Agent B 的实现、原测试、合同、研究状态或目录外文件。真实供电、真人 owner、
真实付款 rail 和真实产品均为 `NOT_RUN`。

## 红灯演化

### H0：B 原套件绿，攻击仍大面积失败

首次接手时：

```bash
python3 -m unittest discover -s tests -v
```

结果为 `18/18 PASS`。B 随后增加独立 failure-injection denominator，原生测试变为
`19/19 PASS`。

Agent C 首轮独立攻击：

```bash
python3 -m unittest tests/test_attack.py -v
```

结果为 `1/11 PASS, 10/11 FAIL`。其中一条断言后来被 Agent C 主动纠正：
pre-existing state 可以匹配 current Q，真正必须保持 false 的是 exact-attempt causality 与
episode contribution，而不是笼统要求 Q binding false。纠正后为：

```text
3/11 PASS
8/11 FAIL
full discovery: 22/30 PASS, 8/30 FAIL
```

### H1：首轮修复关闭八类 response/transplant 红灯

首轮有效红灯及修复后的行为如下：

1. **wrong-target Authority applicability**
   - 原问题：O_S 对 C7 的 raw `AUTHORIZED` 被呈现得像也覆盖 C8。
   - 当前：保留 raw owner truth，同时明确
     `authority_covers_actual_object=false`、`episode_contribution=FALSE`、
     `CountsTowardQ=false`、`recovery=REQUIRED`。
2. **occurrence owner/domain transplant**
   - 原问题：O_R / resource response 可靠字段同形冒充 O_E target-native Effect。
   - 当前：必须为 `owner_id=O_E` 且 `domain=TARGET_NATIVE`。
3. **episode substitution**
   - 原问题：另一个 `Attempt.episode_id` 仍可计入当前 episode。
   - 当前：episode、Q、operation、target 和 causality 分别校验。
4. **Authority owner/actor/time transplant**
   - 原问题：wrong owner、wrong actor、post-attempt Authority 可计数，且 method 可能先执行。
   - 当前：执行前校验 O_S、operation、actor、object、Q 与
     `observed_at <= attempted_at`；不满足时不调用 execute。
5. **无 observation 冒充 refusal**
   - 原问题：零 attempts、零 owner query 也返回 `BOUNDED_REFUSAL_NO_EFFECT`。
   - 当前：先查询 episode status，保持 `BOUNDED_UNKNOWN`；只有明确 owner denial 才是 refusal。
6. **Adoption transplant**
   - 原问题：另一个 effect/episode/owner 的 TRUE 可继续 Settlement。
   - 当前：绑定 O_V、exact effect、episode 且必须在 Effect 之后。
7. **单 owner Acceptance**
   - 原问题：同一 O_Q response 可同时满足 O_Q 与 O_V。
   - 当前：要求 owner set 恰为 `{O_Q,O_V}`，分别绑定 effect、episode、Q 与 Effect 后时点。
8. **provider / wrong obligation / wrong scheme finality**
   - 原问题：同形 phase 名称可冒充 O_P finality。
   - 当前：O_P obligation 与 phase obligation/scheme identity 均进入 finality gate。

### H2：扩大攻击后又发现三个红灯

在首轮 `30/30` 修复报告后，Agent C 将攻击扩到 20 项，实际出现：

```text
17/20 PASS
3/20 FAIL
```

三个新红灯：

1. O_P owner 正确但 `obligation.effect_id` 属于另一个 Effect，仍可结算当前 Effect；
2. `observed_at=20` 时，`phase.observed_at=999` 的未来 phase 仍可建立当前 finality；
3. 同一 operation 产生两个不同 occurrence ID 时，只按 ID 去重，未识别 duplicate Effect。

当前修复分别为：

- `expected_effect_id` 进入 O_P obligation assessment；
- phase 只有 `phase.observed_at <= observed_at` 才能推进当前图；
- duplicate 同时按 occurrence ID 与 operation ID 检测，发现后返回 `DUPLICATE_EFFECT`。

### H3：曾出现一次 recovery 假绿，最终由 target state gate 关闭

早期修复只验证 recovery event 的字段形状。Agent C 构造了：

```text
O_E-shaped recovery event
reverses_occurrence_id 正确
world.recoveries = []
真实 target state 未变化
```

method 一度仍返回
`RECOVERED_WRONG_TARGET_THEN_EXACT_EFFECT_ACCEPTED_SETTLED`。这是“failure injection 没有
改变真实 target state”的直接反例；之前只排除普通 settled 字符串的测试断言也被 Agent C
纠正，未把假绿保留为成功。

最终实现新增独立 O_E target-state truth surface：

```text
recover command
→ recovery occurrence readback
→ exact object current-state readback
→ state == original.from_state
→ state observation not older than accepted recovery event
```

simulator 的 `recover()` 同时实际更新 `target_states`。仅返回同形 recovery event、没有状态
变化的攻击现在保持 `RECOVERY_UNKNOWN/BOUNDED_UNKNOWN`，不能闭合 episode。

## E3 hidden pair 专项

原 E3A plan 是一个 attempt，E3B plan 是两个 attempt，且 case ID 直接写出
`EFFECT/NO-EFFECT`；这会在 interaction 前泄露分支。最终两支对 method 完全共享：

```text
public case = E3-ACK-LOST-OPAQUE
attempt count = 2
operation IDs / actors / targets / timing = same shape
```

正确分叉只来自 owner readback：

- E3A 首次 readback 找到 exact Effect，停止，不执行 fallback；
- E3B 首次 readback保留 wrong-target raw occurrence，完成 target-state recovery 后才执行
  fallback。

E3B 的成功 resolution 没有擦除失败历史：最终结果仍含 1 个 C8 raw Effect、
`CountsTowardQ=false`、`recovery=REQUIRED`，以及独立 recovery occurrence。

## 最终独立复跑

Agent C 在 B 宣告修复后从稳定目录重新执行：

```bash
python3 -m unittest \
  tests.test_attack.SettlementAndRecoveryAttacks.test_structurally_valid_recovery_event_without_state_mutation_cannot_close \
  -v
python3 -m unittest tests/test_attack.py -v
python3 -m unittest discover -s tests -v
python3 run.py --mode all
```

结果：

```text
target-state forged recovery: 1/1 PASS
Agent C attacks:             20/20 PASS
full suite:                  41/41 PASS

semantic conformance:         6/6 PASS
local synthetic E2E:          8/8 correct resolution
exact task success:           6/8
failure injection:            4/4 PASS
raw occurrences:              8
wrong-target real effects:    1
recoveries:                   1
duplicate effects:            0
owner API calls:             70
```

semantic、E2E 与 failure injection 是三个独立 denominator，没有相加成一个总分。

## alias、truth-copy 与证据面

- `method.py` 不导入 scenario、world、fixture 或 expected label；method 只持有 owner API
  capability，raw trace 为逐 endpoint receipt，不是完整 owner packet。
- owner response 的 owner/domain/object/episode/Q/actor/time 适用关系已由攻击覆盖；字段同形
  transplant 不再自动生效。
- 本线只有一个 G6 method，没有多 arm 方法比较；因此这里既无 `_common_candidate` 式 alias
  胜者，也不能据此主张多实现独立性、成熟产品等价或 method winner。
- public plan 是 G1–G5 上游产物；本线结果不能反向证明 plan formation、Authority formation
  或 discovery 已被解决。
- E3 hidden pair 在当前 synthetic author 下同构，但尚不是不同 truth author 的 blind
  holdout。

## 第一轮最窄判断（历史）

```text
G6_SEMANTIC_CONFORMANCE = POSITIVE_SCOPED_LOCAL_SYNTHETIC
G6_ATTACK_SUITE = 20_OF_20_PASS
WRONG_TARGET_RAW_HISTORY = PRESERVED
WRONG_TARGET_AUTHORITY_APPLICABILITY = EXPLICIT_FALSE
PREEXISTING_VS_EXACT_ATTEMPT = SEPARATED
OWNER_RESPONSE_TRANSPLANT_RESISTANCE = POSITIVE_FOR_TESTED_ATTACKS
EFFECT_ADOPTION_ACCEPTANCE_SEPARATION = POSITIVE_FOR_TESTED_ATTACKS
SETTLEMENT_OBLIGATION_SCHEME_FINALITY_REVERSAL = POSITIVE_FOR_TESTED_ATTACKS
RECOVERY_TO_TARGET_STATE = POSITIVE_FOR_LOCAL_SIMULATOR
E3_METHOD_VISIBLE_PREFIX = OPAQUE_SAME_SHAPE
LOCAL_SYNTHETIC_E2E_CORRECT_RESOLUTION = 8_OF_8
LOCAL_SYNTHETIC_EXACT_TASK_SUCCESS = 6_OF_8
REAL_PRODUCT_EXECUTION = NOT_RUN
PRODUCTION_EFFECT = NOT_RUN
HUMAN_ACCEPTANCE = NOT_RUN
PAYMENT_FINALITY = NOT_RUN
INDEPENDENT_TRUTH_AUTHOR_HOLDOUT = NOT_RUN
```

这支持的是本地合成 G6 module 在已测试攻击下的语义与执行边界，不支持 CE-001 全链闭合、
真实产品解决、现实 Effect/Acceptance/Settlement、或新机制必要性结论。
