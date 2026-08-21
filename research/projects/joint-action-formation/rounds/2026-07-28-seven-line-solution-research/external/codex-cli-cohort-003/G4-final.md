# Codex CLI cohort 003 — G4 reliance/outcome module

日期：2026-07-30  
状态：`LOCAL CE-001 COMPONENT MODEL TESTED / BLIND INTERFACE IMPLEMENTED /
NO ARM COMPARISON / NO FORMAL PROMOTION`

## 结论

本轮已在
`experiments/wave-012-ce001-power-restoration/g4-reliance/`
实现一个可运行的 CE-001 G4 局部模块。它强制保存：

```text
P0
→ read-only interaction
→ P1
→ reservation
→ commit-time owner evidence
→ first attempt
→ exact-object readback
→ reconciliation / optional idempotent retry
→ Y_success / Y_resolution / Y_effect / Y_acceptance
```

当前最窄正结果是：

- E3A/E3B 在 attempt 前 raw transcript 同构；
- exact `operation_id × object_id × Q_version` reconciliation 是合法分流 witness，因此
  E3 是 `ACTIVE` pair，不是 full-interaction 不可区分 pair；
- ACK 丢失、wrong-object success、并发重复投递和 reserve 后撤销进入了实际状态转换；
- 首次 success、最终 Effect、resolution 与 Acceptance 没有合并；
- 预测指标与 arm 改变本地 simulator world 的 outcome delta 分开报告；
- worker 不收到 private case identity、transition mode、expected label 或 holdout path。

这不证明 G4 已解决，更不证明完整 CE-001 episode、真实产品或新机制必要性。

## 实际内部 Agent

本 CLI 按 `COMMON.md` 实际建立并收到三名内部 Agent 的返回：

1. `/root/g4_problem_rebuild`（A，只读）
   - 独立重建 G4 原始问题、时间谱系、E3 pair、commit/readback 边界和评分分账；
   - 明确 E3 应归 `ACTIVE`，E3B retry 不得回填首次 `Y_success`；
   - 未写文件。
2. `/root/g4_module_impl`（B，实现）
   - 只写 `g4-reliance/`；
   - 实现 owner/target state machine、blind JSONL worker、broker、fixture、tests、raw trace
     和 failure history。
3. `/root/g4_adversarial_audit`（C，只读、未读取 A/B 返回）
   - 在不知道期待赢家的前提下预注册 truth-copy、alias、目标偷换、伪成功、
     commit-time evidence 穿越、wrong-object、double-submit、revoke、量词和混分攻击；
   - 未写文件。

三者与根会话属于同一模型家族、同一仓库和同一研究传统；这增加了职责与失败路径隔离，
不构成外部独立复现。最终证据解释与一次 truth-boundary 修复由根会话负责。

## 交付

- `module.py`：owner/target 状态机、reservation、commit evidence、target idempotency
  ledger、四 outcome、pair auditor 与分离评分；
- `worker.py`：standalone JSONL policy，只消费 public episode、action names 和 raw response；
- `runner.py`：phase gate、空临时 cwd subprocess broker、holdout scorer、raw/failure trace；
- `public_fixture.json` / `private_holdout.json`：公开接口与 broker-only transition config；
- `tests/test_g4.py`：11 项定向测试；
- `README.md`：运行、语义与证据边界；
- `FAILURE_HISTORY.md`：红灯和根会话修订历史。

本轮没有建立 arms，也没有共享 `_common_candidate`、`choose(packet)` 或 decision root 后
伪比较方法。成熟产品、通用模型、平台直达、强中心和人工制度均为 `NOT_RUN`。

## 精确运行结果

### E3 ACK-loss pair

| case | first `Y_success` | attempts | final Effect | resolution | Acceptance | duplicate | wrong-object reliance | unreconciled |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| E3A effect happened | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 |
| E3B no effect before retry | 0 | 2 | 1 | 1 | 1 | 0 | 0 | 0 |

两侧 submit response 都为 `None`，且 wrong-object endpoint 都先返回另一个 circuit 的 success。
worker 必须再调用 exact reconciliation：

- E3A 读到 exact occurrence，不重复 Effect；
- E3B 读到 authoritative `NO_RECORD` 后，使用同一 operation-level idempotency binding
  安全 retry；
- E3B 最终 `Y_effect=1`，但首次 `Y_success` 仍为 0。

### Pair 量词

- passive：初始 public packet 相同；
- active：pre-attempt transcript 同构，存在 exact reconciliation 分流 witness；
- full-interaction：对声明的有限 protocol grammar 的 7 个 prefixes 逐一比较，1 个 plan
  形成分流，所以 `interaction_equivalent=false`。

这只否定当前 E3 pair 的 full-interaction equivalence。它没有建立 full-interaction
不可能性，也没有用有限枚举冒充开放世界全称。

### Double-submit / revoke

- duplicate-delivery 压力使用 `threading.Barrier(2)`：
  `barrier parties=2 / target deliveries=2 / exact Effects=1`；
- reserve 后、commit 前 O_R 撤销：
  `attempts=0 / Effects=0 / Y_resolution=1 / UnsafeEffect=0`；
- 四个 case 合计：
  `DuplicateEffect=0 / UnsafeEffect=0 / WrongObjectReliance=0 /
  UnreconciledEffect=0`。

当前 revoke 只覆盖 `after reservation / before commit` cutpoint；其他 revoke 时序和跨
runtime old/new epoch race 尚未运行。

### 分离评分

`scores.prediction_calibration` 与 `scores.world_change` 是两个 namespace，没有总分：

- P0 对四 outcome 全部 abstain；
- P1 只对 resolution 作 `YES`，得到 `TP=4`、selective coverage `1.0`；
- P1 对 success/effect/acceptance 仍全部 abstain；
- 同 private transition configuration 的本地 matched no-interaction twin：
  interaction 路径 `3/3` achievable cases 形成 Effect，对照 `0/3`，delta `+3`。

因此可以写“当前 arm 在本地状态机里改变了 target world”，不能写“预测已校准”或“预测
方法更优”。matched twin 也是确定性 simulator 对照，不是现实随机化因果估计。

### Blind interface

- private holdout SHA-256 before/after：
  `3f5bb3b5c1f7290d70847fc8886d8c9a6eda19a9635113bace24c9e0578b6bf0`；
- worker start message 只有 `episode / available_actions / type`；
- worker source 不含 private holdout path 或四个 private case ID；
- holdout 不含 expected-label table；
- subprocess 从空临时 cwd 以 `python3 -I` 运行。

这是 interface/process isolation。private truth 仍由同 cohort 编写，而且同一 Unix user
下的恶意 worker 仍可能扫描仓库，所以：

```text
BLIND_HOLDOUT_INTERFACE = IMPLEMENTED
INDEPENDENT_TRUTH_AUTHOR = NOT ESTABLISHED
HOSTILE_OS_ISOLATION = NOT ESTABLISHED
BLIND_GENERALIZATION_RESULT = NOT RUN
```

## 红灯与根会话攻击

保留了三类真实失败：

1. test-first 首跑因 `module.py` 尚不存在得到 `ModuleNotFoundError`；
2. 首个完整实现虽 10/10 绿，但 worker streams 未关闭，产生 `ResourceWarning`；修复后
   干净通过；
3. 根会话复核发现 `WrongObjectReliance` 曾读取 worker 自报
   `wrong_object_rejected`。这会允许 solver 自造评价事实。现已改为只由 service 观察到的
   wrong-object readback 与 exact reconciliation 状态推导，并加入 worker 正反撒谎都不能
   改变 outcome 的测试。

第三项修复后，定向测试从 10 项增加为 11 项。

## 实际验证

在 `g4-reliance/` 运行：

```bash
PYTHONPYCACHEPREFIX=/tmp/ce001-g4-pycache \
python3 -m unittest discover -s tests -v

PYTHONPYCACHEPREFIX=/tmp/ce001-g4-pycache \
python3 runner.py --self-test

PYTHONPYCACHEPREFIX=/tmp/ce001-g4-pycache \
python3 -m py_compile module.py worker.py runner.py tests/test_g4.py
```

根会话最终复跑：

```text
unittest = 11/11 PASS
runner = SELF_TEST_PASS
py_compile = PASS
```

## 能支持与不能支持

当前能支持：

- 本地 CE-001 component model 中，P0/P1、reservation、commit evidence、attempt、
  readback、reconciliation 和四 outcome 可以保持时间与 truth-owner 边界；
- E3A/E3B 可由 exact-object reconciliation 分流，并在当前 adapter 下避免指定
  duplicate、wrong-object 与 unreconciled failures；
- 当前有限 pair auditor 能区分 passive、active 与 full-interaction 三种证明责任；
- calibration 与 local world-change outcome 可以分账。

当前不能支持：

- 真实 3kW/45min 临时供电、真人 Authority、拒绝、Acceptance 或 Settlement；
- 任何真实成熟产品、平台、中心、通用模型或人工制度已经运行或获胜；
- 生产并发、跨 runtime restart/migration、全部 revoke cutpoint 或长期可靠性；
- 独立 blind holdout、普遍预测校准或一般 full-interaction 不可能性；
- CE-001 八 case、G1–G7、Problem v1/v2 或 G4 scoped claim 已闭合；
- candidate-exclusive success、新协议必要或任何正式状态晋升。

## 下一接口

下一项高价值工作不是增加同作者 case 数，而是由不同 truth author 在 candidate source hash
冻结后生成并密封新的 public/private holdout，至少加入：

- unseen ACK-loss/readback delay 与 authoritative-absence 边界；
- `before reserve / after reserve / concurrent with commit / after Effect` revoke cutpoints；
- old/new runtime、target restart 与 operation-level double-submit；
- rename/order/truth-transplant mutations 和多个 scheduler seeds；
- matched passive/formation twins，使 world-change delta 不依赖同一手写 transition author。

只有该接口被真正盲运行并由第二实现复现后，才能讨论当前 local residual 是否稳定。当前
没有合同缺陷需要改写，故不登记 `CONTRACT_REOPEN_CANDIDATE`，也不修改 NOW、PROGRAM、
Problem、LineContract 或机制状态。
