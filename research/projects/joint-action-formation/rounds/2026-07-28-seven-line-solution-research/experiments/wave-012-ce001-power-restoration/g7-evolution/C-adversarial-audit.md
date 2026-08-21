# CE-001 / G7：Agent C 敌对审计

日期：2026-07-30  
身份：`G7 INTERNAL AGENT C / adversarial auditor`  
被审实现：`G7_INTERNAL_AGENT_B`  
状态：`PRE-REPAIR 12 RED OF 14 / POST-REPAIR 17 OF 17 PASS /
NO METHOD WINNER / NO FORMAL STATUS CHANGE`

## 0. 结论

Agent B 的首批 happy-path runner 能实际跑完 E4/E6，并在原 13 项测试中全绿；但这组绿灯
不能支持 E4/E6 已闭合。Agent C 在不读取 private expected label、不预设方法赢家、也不修改
Agent B 源码的条件下，新增 14 项合同级攻击，得到：

```text
ADVERSARIAL_TESTS = 14
RED = 12
PASS_CONTROLS = 2
ERROR = 0
```

最承重的 false-green 不是格式问题：

- repeat Context 可以把旧 `Q_version`、目标对象、operation、semantic effect key、history
  root 与 evidence label 偷换后继续；
- E4 可以把旧 primary Effect 的 `DEDUPLICATED` readback 当成 alternative
  recovery-to-value；
- E4 的 history chain 即使已被攻击改坏，输出仍硬编码
  `history_prefix_preserved=true`；
- E6 把 `Q@v1 / Circuit-C7` 改为新 Q/新目标后，target 与 Acceptance 同时复制被改 packet，
  仍自证 `ExactTaskSuccess=true`；
- old-runtime fence 只依赖同一个内存对象中的 epoch；注入
  `TARGET_RESTART_LOSES_EPOCH` 后旧 runtime 得到 `DEDUPLICATED`，不是真实
  `FENCED_OR_DENIED`；
- capsule 只要保留字段路径，空 obligation 仍可导入；field-loss 的安全停机又被命名为
  `CorrectResolution=true`，混淆“攻击安全通过”与“migration portability 成功”。

因此首批实现的最窄状态是：

```text
E4_E6_HAPPY_PATH_LOCAL_COMPONENT_RUN = POSITIVE_SCOPED
EXACT_BINDING_UNDER_TRANSPLANT = FAIL
E4_PRIOR_EFFECT_RECONCILIATION = FAIL
E4_HISTORY_REWRITE_DETECTION = FAIL
E6_DURABLE_OLD_RUNTIME_FENCE = FAIL
CAPSULE_SEMANTIC_SUFFICIENCY = FAIL
COLD_REPEAT_NET_VALUE = NOT_MEASURED
HIDDEN_PAIR = NOT_CONSTRUCTED
G7_CE001_SOLUTION = NOT_ESTABLISHED
```

## 1. 独立性与读取边界

我以 `G7 INTERNAL AGENT C` 身份执行，只写：

- `tests/test_adversarial.py`
- `C-adversarial-audit.md`

没有修改 Agent B 的 `g7evo/`、fixture、runner、原测试或 raw result。攻击前完整读取了根
`AGENTS.md`、`research/NOW.md`、cohort-003 `COMMON.md`、`CE-001-CONTRACT.md`、
cohort-002 `ROOT-ADVERSARIAL-AUDIT.md` / `SYNTHESIS.md`、Wave-011 G7 final/README/
tests，以及 Agent A 的完整重建。

实现中没有可供我读取的 private oracle；`private_expected_label` 的值只是 `ABSENT`。
这排除了直接 expected-label copy 的一个浅攻击，却没有形成 owner truth 与 solver/result
的独立分母。下文的 Q/目标偷换证明：target 与 Acceptance 读取同一被改 packet 时，仍可形成
更隐蔽的 truth self-copy。

## 2. 实际命令与数字

首批实现落盘后的原生运行：

```bash
PYTHONPYCACHEPREFIX=/tmp/g7c-pycache python3 runner.py
PYTHONPYCACHEPREFIX=/tmp/g7c-pycache python3 -m unittest discover -s tests -v
```

当时结果：

```text
runner: case_count=2, exact_task_success=2, correct_resolution=2
original tests: 13/13 PASS
```

Agent C 冻结攻击集后的运行：

```bash
PYTHONPYCACHEPREFIX=/tmp/g7c-pycache \
  python3 -m unittest tests.test_adversarial -v
```

实际结果：

```text
Ran 14 tests in 0.044s
FAILED (failures=12)
PASS=2
ERROR=0
```

这 12 项是 pre-repair 红灯。后续即使修复后转绿，也必须保留本节红灯历史，不能用最终绿灯
改写首次 false-green。

## 3. 红灯逐项

| ID | 攻击 | 实际观察 | 影响 |
|---|---|---|---|
| C-RED-01 | repeat prior Context 将 `object_id/Q_version` 换成 `Circuit-C8/Q@attacker` | 仍返回 `CONTINUE` | exact target/Q 没绑定 current packet |
| C-RED-02 | repeat 将 `operation_id/semantic_effect_key` 换成新 identity | 仍返回 `CONTINUE` | cached permit 可穿到新因果/Effect 身份 |
| C-RED-03 | repeat 注入任意 `history_root`、authority hash、safety evidence hash | 仍返回 `CONTINUE` | hash 是不可验证 label，不是 provenance |
| C-RED-04 | Context 保留字段名但把 evidence list、history root、effect key 置空 | `validate()` 返回空违规集 | 只验 presence，不验语义充分性 |
| C-RED-05 | 要求 cold/repeat 保存冻结成本轴 | 缺 disclosure、wait、compute/tool、formation/setup、assurance、recovery/migration、governance、opportunity loss 八轴 | `2 queries > 1 query` 不能支持 lifecycle 降本 |
| C-RED-06 | target 预置 primary 的同 semantic-key Effect，再运行 E4 alternative | dispatch=`DEDUPLICATED`，仍 `RecoveryToValue=true` | 未区分旧 Effect 对账与 R2 恢复到价值 |
| C-RED-07 | 在 `DEFEATER_APPENDED` 后改写首条 history payload | emitted chain 无法重新 import，结果仍 hard-code prefix preserved | history rewrite 指标可假绿 |
| C-RED-08 | E6 packet 改为 `Q@v2-substituted / Circuit-C8` | Acceptance=`ACCEPTED` 且 ExactTaskSuccess=true | 冻结 Q/目标被同源复制后自证成功 |
| C-RED-09 | takeover 时注入 target restart 丢 epoch | old runtime outcome=`DEDUPLICATED`，非 fenced | 当前 fence 不是跨 runtime durable fence |
| C-RED-10 | capsule `obligations=[]` 并重新 hash | importer 仍 `imported=true` | path/schema 成功不等于义务语义保真 |
| C-RED-11 | 删除 `pending_acceptance` | import 安全拒绝，但输出 `CorrectResolution=true` | fail-closed 被混成 portability 成功口径 |
| C-RED-12 | 不实例化 hidden pair 且无显式状态 | fixture 未写 `HIDDEN_PAIR=NOT_CONSTRUCTED` | 不能知道 safety-liveness 是否被测试 |

其中 C-RED-01 与 root 独立 mutation 的 `RED-001-ROOT-EXACT-BINDING-TRANSPLANT`
相交；这不是两份独立证据，而是同一缺陷被两条执行路径复现。

## 4. 两个通过的控制

### 4.1 safe stop 没有冒充 E4 recovery-to-value

把 alternative lease 也改为 revoked 后，`run_e4()` 返回：

```text
final_action=BLOCK
RecoveryToValue=false
ExactTaskSuccess absent/false
```

所以“只安全停止冒充 E4 恢复”在这个窄 mutant 上没有复现。边界是：`run_all()` 尚未把该
负结果规范成完整 case vector；本控制只证明没有把 block 标成 recovery。

### 4.2 unknown capsule schema 已被拒绝

把 capsule schema 改成 `unrelated.schema.v999` 并重算 hash 后，importer 拒绝。这个检查是
Agent C 首轮读取后、Agent B 并行加入的 semantic gate，复跑时已通过。

它只关闭“任意 schema 都可 import”。两 adapter 的函数签名不同仍不构成语义独立性证明；
空 obligations 可导入、target 没有第二套 native obligation/runtime model，故 alias 风险
没有关闭。

## 5. 按用户指定攻击面的判断

### truth-copy / private-label leak

没有发现源码读取 private oracle 或 expected action；直接 label leak 未复现。更严重的
替代路径已复现：E6 的 target、readback 与 Acceptance 共同消费同一被改 operation packet，
使错误 Q/目标变成“authoritative”成功。当前应记
`DIRECT_PRIVATE_LABEL_LEAK=NOT_OBSERVED`、`SAME-SOURCE_TRUTH_SELF-CERTIFICATION=FAIL`。

### 两个 adapter 语义 alias

owner adapter 与 capsule adapter 的 Python signature 不同；unknown schema 也会拒绝。
但 importer 只把同一 v1 payload 展平，没有第二个 native state、resume primitive 或未结
义务 materialization。空 obligations 仍通过，故只能记
`SIGNATURE_DISTINCT=true / SEMANTIC_INDEPENDENCE=NOT_ESTABLISHED`。

### 目标对象 / Q_version 偷换

C-RED-01 与 C-RED-08 均实际复现。前者是 repeat cache 穿透，后者是 E6 完整
target-readback-Acceptance 自证链。当前为 `FAIL`，不是只缺测试。

### E4 recovery-to-value 与 Effect 对账

safe stop 没有被标成 recovery；但已有 primary Effect 被 semantic-key dedupe 后仍被算作
alternative recovery。effect count 保持 1 并不等于 E4 已经由替代方恢复价值，必须绑定
Effect 来源、旧路径 reconciliation 与 alternative 后置状态。

### history rewrite

`AppendOnlyHistory.import_verified()` 本身能拒绝被改链；E6 nominal 也实际比较 source
prefix。缺陷集中在 E4：结果字段硬编码 `true`，不从输出 history 复算。故 primitive 有用，
E4 claim gate 失败。

### E6 old-runtime fence

nominal 同一对象、epoch 不丢时确实返回 `FENCED_OR_DENIED`。一旦模拟 contract 已列出的
`TARGET_RESTART_LOSES_EPOCH`，旧 runtime 只被 semantic-key dedupe，没有被 fence。当前
最多支持 single-process volatile-epoch regression，不能支持 cross-runtime fence。

### capsule field loss

删除 required path 后 importer 会 fail closed，这是安全正结果；但把它写为
`CorrectResolution=true` 会让攻击安全与 R8 portability 混合。完整 capsule也仍缺
obligation 内容校验。应分别报告 `FieldLossSafetyPass` 与 `MigrationPortabilitySuccess`。

### cold/repeat cost 与 Context

cold/repeat 当前固定主要差异是 owner query `2 vs 1`；缺八个合同成本轴，没有独立 lane、
同 schedule、value loss 或 Pareto 比较。Context 的字段集合精确相等测试只是 shape；
present-but-empty、wrong binding 和不可验证 hash 仍通过。没有观察到 Context 过量泄漏，
但“最小”与“充分”都未被当前实验建立。

### hidden pair

本实现没有构造 hidden pair。合同把 pair 作为条件攻击，不强制每个 G7 module 都实例化；
因此正确修复不是虚构一对 world，而是显式写
`HIDDEN_PAIR=NOT_CONSTRUCTED / SAFETY_LIVENESS_FRONTIER=NOT_RUN`，且不输出相关通过率或
结论。若未来实例化，valid 与 revoked 必须有相反 final requirement。

## 6. 当前能支持与不能支持

能够支持：

- 两个本地合成 happy path 可执行并产生 raw trace；
- owner lease/safety adapter 有不同 native call shape；
- unknown capsule schema 会拒绝；
- required path 丢失后可以 fail closed；
- `AppendOnlyHistory.import_verified()` 能发现被改 hash chain；
- E4 无合法 alternative 时不会把 block 标为 recovery-to-value。

不能支持：

- E4 已完成 prior-Effect reconciliation 或真实 alternative recovery；
- E6 绑定了冻结 Q/target，或 old runtime 被 durable fence；
- capsule 在第二个独立 runtime 中语义可移植；
- Context 最小充分或 repeat 生命周期净成本更低；
- hidden-pair safety-liveness 前沿；
- 两个 adapter 语义独立；
- 真实产品、真人 Authority/Acceptance、物理供电 Effect、付款、生产迁移或长期净值；
- 任一 arm 胜出、新机制必要/不必要，或 Problem、LineContract、MechanismProfile、
  NOW、PROGRAM、正式 claim 的状态变化。

## 7. 修复后的验收条件

Agent B 后续修复必须用同一 `tests/test_adversarial.py` 复跑，并保留本轮 12 RED 历史。绿灯
只说明这些具体 mutant 被关闭，还需保持以下边界：

1. repeat 逐项绑定 current packet 的 Q/object/operation/effect identity，并验证 history
   与 evidence provenance；
2. E4 先对账 primary Effect，`DEDUPLICATED` 不能自动算 alternative recovery；
3. E4/E6 的 history、unsafe、duplicate、wrong-object、unreconciled 指标从 owner/target
   records 复算，不由 candidate 自报；
4. E6 exact success 对冻结 Q@v1/Circuit-C7 独立评分；
5. fence 状态进入 effector 的 durable authority domain，并覆盖 restart-loss；
6. capsule 校验 obligation 内容；field-loss safety 与 portability 分开；
7. cold/repeat 未补齐同分母生命周期成本前，删除“repeat cheaper”结论；
8. hidden pair 未构造就显式 `NOT_CONSTRUCTED / NOT_RUN`。

本审计没有修改 Agent B 源码，也不创建 `external/G7-final.md`。

## 8. Post-repair 独立复跑

Agent B 没有删除 pre-repair 红灯语义，而是先修复原冻结 14 项攻击。Agent C 复读修复后
实现时，又构造了三个更深的边界攻击：

1. 首版所谓 durable fence 仍是同一个 `EffectTarget` 对象的字段；新建 target 后旧 epoch
   可以 `COMMITTED`；
2. adapter 只有 signature 差异，却没有显式把 semantic independence 保持为 Unknown；
3. 补齐 lifecycle cost 列以后，各值仍是 fixture 账，缺少“不构成完整测量”的状态边界。

这三项实际运行均为 RED：

```text
POST_REPAIR_EXTENSION = 17 tests
NEW_RED = 3
PASS = 14
```

最终修复采用了与攻击相称的边界：

- 新增显式 `DurableFenceAuthority`，以同一外部 authority/ledger 注入 old/new
  `EffectTarget`；Agent C 的跨新对象攻击不使用 class-global owner-id 状态，而让两个实例
  共享同一 authority 后验证旧 epoch 被拒；
- adapter evidence 显式返回 `semantic_independence=NOT_ESTABLISHED`，不再由签名差异推出
  语义独立；
- E4 Context 显式返回
  `cost_comparison_status=NOT_MEASURED_FULL_LIFECYCLE`，成本列不产生净赢家。

最终由 Agent C 独立执行：

```bash
PYTHONPYCACHEPREFIX=/tmp/g7c-final-pycache \
  python3 -m unittest tests.test_adversarial -v

PYTHONPYCACHEPREFIX=/tmp/g7c-final-pycache \
  python3 -m unittest discover -s tests -v

PYTHONPYCACHEPREFIX=/tmp/g7c-final-pycache \
  python3 runner.py --output raw/run-traces.json

PYTHONPYCACHEPREFIX=/tmp/g7c-final-pycache \
  python3 -m py_compile runner.py g7evo/*.py tests/*.py
```

最终结果：

```text
adversarial: 17/17 PASS in 0.068s
full suite: 33/33 PASS in 0.219s
runner: case_count=2, exact_task_success=2, correct_resolution=2, audit_status=PASS
py_compile: PASS
```

中途全套曾因 Agent B 修改 alternative commitment event schema、原测试仍读取旧
`payload.reservation.resource_id` 而出现 `33 tests / 1 ERROR`；修复证据接口后才得到上述
33/33。该 integration red 也不应由最终绿灯改写掉。

### 最终最窄判断

17/17 与 33/33 只说明本审计列出的具体 mutation 已关闭或诚实降级，不把本地组件模型提升为
完整 G7 结果。当前可以把状态从“已知 false-green”收窄为：

```text
E4_E6_LOCAL_HAPPY_PATH = 2/2
KNOWN_C_AGENT_MUTATIONS = 17/17 CLOSED_OR_HONESTLY_BOUNDED
HIDDEN_PAIR = NOT_CONSTRUCTED
SAFETY_LIVENESS_FRONTIER = NOT_RUN
ADAPTER_SEMANTIC_INDEPENDENCE = NOT_ESTABLISHED
COLD_REPEAT_FULL_LIFECYCLE = NOT_MEASURED
REAL_PRODUCT_OR_PRODUCTION = NOT_RUN
FULL_CE001_EIGHT_CASE = NOT_RUN
G7_GENERAL_SOLUTION = NOT_ESTABLISHED
```

独立 fence 仍是本地合成 authority/ledger，不是跨进程持久服务、外部账本或生产目标端证明；
Context hash 也只在当前受信组件模型内阻止已列 transplant，不是对同权限恶意进程的密码学
保证。最终绿灯因此支持“这套局部 harness 比首批实现更难伪成功”，不支持方法胜者、现实
恢复、通用语义可移植或新机制判定。
