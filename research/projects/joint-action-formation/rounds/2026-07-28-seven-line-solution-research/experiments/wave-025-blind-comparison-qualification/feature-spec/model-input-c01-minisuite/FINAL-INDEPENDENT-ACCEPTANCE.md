# C01 minisuite V2 最终独立窄验收

> 审查对象：`model-input-c01-minisuite` V2 当前字节与 `POST-FIX-AUDIT.md`  
> 方法：同一红队 reviewer，先读修复说明但不继承其结论；重跑五个 blocker、构造嵌套输入绕过、
> 核对来源与完整快照  
> 最终决定：`ACCEPT_SCOPED_C01_MINISUITE = NO`  
> 原因：F4、stable、F1 OOV、P2 边界已经关闭；但 phase boundary 仍只是 stdin 约定，不是能力隔离，
> 且 feature row ID 可由公开 generator 反推出全部 synthetic labels。

## 1. 分层裁决

| 层级 | 最终状态 | 说明 |
|---|---|---|
| 当前五份 canonical artifact 的可重建性 | `ACCEPT` | `--check` 通过，5 artifacts byte-exact；全套 163 tests 通过，前后 hashes 不变 |
| F4 不补义 | `ACCEPT` | candidate=0、rule=null、固定 underdetermined failure；P6 不再伪恢复 |
| stable 定义 | `ACCEPT` | calibration 与 holdout 两阶段双类 recall 都进入判定 |
| F1 OOV truth table | `ACCEPT` | unknown 被忽略，唯一 selector presence/absence 分支，四格真值一致 |
| P2 来源边界 | `ACCEPT` | 明确 conditional/Unknown，不再声称公开 D1 已绑定跨 phase premise |
| feature 明文 marker 清除 | `ACCEPT_NARROW` | 当前 artifact 中无明文 R/S、role-r/role-s；但 label 仍可由 row ID + 公开 source 100% 恢复 |
| calibration permutation noninterference | `ACCEPT_ALGORITHMIC` | 固定 feature bytes 下反转 calibration labels 不改 universe bytes；但不构成 capability blindness |
| freeze/score 真实能力边界 | `REJECT` | 同权限 child 可直接读 labels artifact；nested labels/feature rows 可穿过所谓 closed input |
| scoped C01 minisuite | `NOT_ACCEPTED` | 最承重的“holdout labels 对 freeze 不可读”主张不成立 |
| actual D0/D1 | `UNKNOWN / NOT_RUN` | 无 actual V2S receipt、fresh formal registry、sensitivity/CI |
| `MODEL-INPUT-V2S` canon | `NOT_A_CANDIDATE` | 本包不能晋升 canon |
| G | `NOT_RUN / NOT_UNLOCKED` | 本轮不授权 G |
| 3200 formal | `NOT_RUN / FORBIDDEN_TO_INFER` | 本轮不授权 formal |

这不是把“同 UID 恶意 controller”无限上纲。任务要求复核的是“真实进程/能力层 phase split 与
holdout label 不可读”。V2 确实增加了两个 OS 进程，但两个进程仍拥有同一工作区读权限，freeze
进程的输入对象也没有递归 closed schema；因此它没有达到自己写下的能力主张。

## 2. clean current snapshot 独立重放

独立运行：

```text
python3 feature-spec/model-input-c01-minisuite/c01_minisuite.py --check
=> byte-exact canonical check passed: 5 artifacts

PYTHONPYCACHEPREFIX=/tmp/wave025-c01-v2-independent-pycache \
python3 -m pytest -q feature-spec/tests \
  feature-spec/collector-v1.1-candidate/tests \
  feature-spec/model-input-c01-minisuite/tests --disable-warnings
=> 163 passed in 55.20s
```

测试前后以下 9 个文件的 SHA-256 完全一致：

| 文件 | bytes | SHA-256 |
|---|---:|---|
| `C01-MINISUITE-CONTRACT.candidate.json` | 2,844 | `c23d974e0bcda29e4ee20b5dd2f57a03cae955bf3be5a9e76d14590ec5b5f88d` |
| `CASES-FEATURES.candidate.json` | 95,830 | `bcb23aad498b04fbf73e5c690424aaa257e1bc0bab800843639e80e248b1330e` |
| `CASES-LABELS.candidate.json` | 33,346 | `bcb8f708d326af8e4162625c3d45e097ccc1b3e01aef156387a2d86b41e7b3a9` |
| `FROZEN-SELECTIONS.candidate.json` | 320,962 | `b2f1031f34005fa6660aa332174db6c0f1ba47f12aa0ce87269c9be3ee955ba3` |
| `RESULTS.candidate.json` | 45,534 | `91df045cea253087434c2d4b92c2fb6bb16e839e30e4af9fe8ac061054a4aabd` |
| `c01_minisuite.py` | 42,157 | `01b298f699f5e971409911d9e975d5fae04d5bda6e87dc969161c009f3efe7cb` |
| `tests/test_c01_minisuite.py` | 12,755 | `7ad192720bf146ae640bba37b0039200fb526a423c907d04aa23d2b78ef39ce3` |
| `README.md` | 6,804 | `66eb199ff4bf0475cc40f7933a94d1467ae5c04d98aaecd379019de52752551e` |
| `POST-FIX-AUDIT.md` | 6,634 | `5930f50e84567311b039118ff62ffc17254f710b0c8f3294ed0e356c30f900ac` |

这确认 post-fix audit 所列最终字节与当前 checkout 相符。测试中的 LibreSSL warning 未被用来支持
任何网络或 TLS 结论。

## 3. blocker 1 重放：进程分开了，能力没有分开

### 3.1 已关闭的部分

正常 orchestrator 的调用顺序确实是：

1. parent 只把 case、calibration labels、contract hash 放进 `--phase-freeze` stdin；
2. child 返回 frozen rule 与 calibration/holdout predictions；
3. parent 才把 frozen package 与 holdout labels 送到另一个 `--phase-score` child；
4. 当前实现的 `select_rule` 不接收 holdout labels，holdout label 全翻转不会改变正常生成的
   `FROZEN-SELECTIONS` bytes。

因此 V1 的“同一函数先 join holdout labels 再选择 rule”已经消失。这是实质进展。

### 3.2 未关闭：freeze child 仍可读 label 文件

`subprocess.run([sys.executable, c01_minisuite.py, --phase-freeze])` 没有建立文件系统 sandbox、独立
UID、只读 allowlist 或临时 capability root。用完全相同的 Python executable/权限启动最小 child，
它可以直接读取：

```text
CASES-LABELS.candidate.json => readable=true, bytes=33346
```

所以 `holdout_labels_available_to_freeze_process=false` 不是观察事实，只能解释为“正常代码没有从
stdin 收到这个字段”。这低于本次要求的能力层不可读。

### 3.3 未关闭：nested labels 绕过 top-level closed shape

`run_phase_freeze` 只检查 payload 顶层 keys：

```text
{calibration_labels, case, contract_sha256}
```

它不验证 `case` 的 closed shape，也不在 child 内调用 `validate_feature_document`。独立最小变异把
40 个真实 holdout labels 放进：

```text
payload.case.holdout_labels
```

phase-freeze 正常返回成功。输出仍写 `holdout_labels_received=false`。这说明该字段是 hard-coded
自述，不是接口 admission 结果。

### 3.4 未关闭：score 的 no-feature-rows 也可嵌套绕过

同理，给 frozen package 增加 `feature_rows`，用变异后 package 的 SHA 作为同一 payload 中的
`frozen_package_sha256`，`--phase-score` 接受并返回成功；每个 family 仍写：

```text
holdout_scoring_consumed_feature_rows=false
```

score 当前算法没有实际使用这些 extra rows，但这证明“score process 不接收 feature rows”不是闭合
接口保证。自带 package 与自带 hash 只能发现传输误码，不能阻止调用者同步替换 package 和 hash。

### 3.5 contract hash 未被消费

把 freeze payload 的 `contract_sha256` 改成 64 个 `0`，child 仍成功，且 frozen package 与正常包
byte-exact 相同。该 hash 目前只是允许的输入键，没有被核对、写入输出或影响选择。

因此 source binding 不能从 parent summary 推导成 child 实际绑定。

## 4. blocker 2 重放：明文消失，但 labels 可由 feature metadata 反推

### 4.1 通过项

当前 canonical feature artifact 中没有以下明文 marker：

```text
"R", "S", role-r, role-s, -r-, -s-
```

row IDs 是固定宽度 `o_` + 24 hex；P1/P2 atom 使用不含 role 名称的 `opaque-atom-*`。固定同一
feature case、只翻转 calibration label join 时，universe canonical bytes 不变，选中 rule/prediction
orientation 改变。因此 `freeze_universe` 当前实现是 calibration-label 参数独立的。

### 4.2 决定性反例：640/640 labels 可恢复

row ID 的定义是公开确定函数：

```text
sha256(domain, case_id, phase, slot)[:24]
```

label assignment 也是同一公开 source 中由 `case_id, phase, slot` 唯一决定的 SHA-256 排序。每个
phase 只有 40 个 slot。只凭 feature artifact 中的 `case_id`、`phase`、`row_id` 和公开 generator：

1. 枚举 slot 0..39，重算 40 个 row IDs；
2. 由 row ID 反查 slot；
3. 调用公开 `label_assignments(case_id, phase)`；
4. 得到该 row 的 class。

独立重放对全部 8 cases、640 rows 恢复了 `640/640` labels，与 labels artifact 完全一致，包括所有
holdout labels。

这不是说 synthetic signal 不应和 labels 相关；P1/P4/P5 本来就是人为构造可区分关系。问题在于
本包同时把 row IDs/assignment algorithm 暴露给 freeze child，又声称 labels 是独立不可读材料。
calibration label inversion test 只证明当前 universe 函数没有接收 labels 参数，不能证明 child 不具备
恢复 labels 的能力。

这个问题即使把 `CASES-LABELS` 文件移出 child 权限域也仍存在；必须让 opaque row ID 与 label
assignment 之间没有可由 child 可读材料重建的公开映射。

## 5. blocker 3 重放：F4 已诚实拒绝

P6/F4 当前结果为：

```text
availability = REJECTED_UNDERDETERMINED_NOT_EXECUTED
candidate_count_generated = 0
selected_rule = null
failure_reason = RULE_FAMILY_SPEC_UNDERDETERMINED_NO_EXECUTION
stable = false
```

候选代码不再生成 `00/01/10/11 -> class` mapping；所有 F4 case 都保持 unavailable。当前结果没有
用 fallback R 的评分把 F4 描述成已执行失败，而是先以 availability/failure code 声明未执行。

这一 blocker 关闭。它不回答 F4 应采用什么语义，正好保留为上层待决问题。

## 6. blocker 4 重放：stable 已包含两个阶段

独立把 calibration 中一个 R 与一个 S label 对调，同时保持 holdout 原样。F1 结果：

```text
calibration BA = 19/20 = 0.95
holdout BA = 1
stable = false
failure_reason = CALIBRATION_RECALL_NOT_EXACT_BOTH_CLASSES
```

代码同时调用 `exact_recall_one(calibration)` 与 `exact_recall_one(holdout)`，和当前绑定 feature spec
的两阶段双类 recall=1 要求一致。此 blocker关闭。

## 7. blocker 5 重放：F1 OOV truth table 唯一

P8 选中 F1 rule 的独立四格预测：

| selector | unknown | prediction |
|---|---|---|
| absent | absent | `absent_class` (`S`) |
| absent | present | `absent_class` (`S`) |
| present | absent | `present_class` (`R`) |
| present | present | `present_class` (`R`) |

unknown token 不扩 universe、不触发 row-level R fallback，`holdout_oov_row_count` 只作诊断。contract、
README、rule bytes、P8 和 predictor 实现一致。此 blocker关闭。

## 8. P2、canonical artifacts 与 source bindings

### 8.1 P2

P2 已改成 `P2_D1_CONDITIONAL_STABLE_EXACT_ATOM`，其 premise 与结果结论都明确写为：

```text
UNKNOWN_CONDITIONAL_CROSS_PHASE_STABILITY_NOT_EXPRESSED_BY_BOUND_PUBLIC_REGISTRATION
```

actual D1 为 `UNKNOWN_NOT_RUN_AND_CROSS_PHASE_STABILITY_PREMISE_NOT_PUBLICLY_BOUND`，旧的“当前公开
D0/D1 都只需 F1”字段已经移除。该来源边界通过。

### 8.2 正确绑定

- `RESULTS.artifact_bindings` 中 contract/features/labels/frozen-selections 四个 hash 与当前五份
  artifact 相符；
- generator/tests/README 三个 implementation hash 与当前文件相符；
- D0 design 与 public control registration 两个外部 hash 与当前来源相符；
- public registration 内的 feature spec hash 仍指向当前 `FEATURE-SPEC.json`；
- `private_control_registry_read=false` 与本包声明边界一致，P2 没再借 private 状态晋升。

### 8.3 限定

这些 parent-level bindings足以支持“当前 checkout 自检重建”，但不能弥补 child 不消费 contract
hash、nested object 不 closed、labels artifact/映射仍可读的问题。163 个测试证明了实现符合当前
测试，而最小绕过说明测试没有覆盖最承重的能力主张。

## 9. 接受所需的最小闭环

要得到 `ACCEPT_SCOPED_C01_MINISUITE`，不需要扩大 C01 或运行 actual D0/D1，只需把两项剩余内部
主张做真：

1. **不可恢复的 label 能力边界**：freeze child 的可读根不包含 labels artifact/private mapping；
   row ID 与 labels mapping 也不能由 child 可读 source/material 枚举恢复。可用独立临时目录、只带
   必要 executable/feature payload 的 subprocess sandbox，或等价 capability机制；
2. **递归 closed input 与外部 expected binding**：freeze/score 对 case、frozen package、predictions
   等嵌套对象做 closed schema validation；拒绝 nested labels/feature rows；freeze 必须核对实际
   contract bytes/hash，score 必须核对由 controller先验持有、不能与 package 同步替换的 expected
   frozen hash。

验收攻击至少应包括：

- child 尝试读取 label path 必须因权限/不存在失败；
- 从全部 feature bytes + child 可读 source 无法恢复高于 chance 的 hidden labels；
- `case.holdout_labels`、row extra field、`frozen_package.feature_rows` 全部 fail closed；
- 错误 contract hash 与同步变异 package/hash 全部 fail closed；
- 正常五 artifact仍 byte-exact，F4/stable/OOV/P2 回归保持。

在这之前，可继续保留 V2 的局部正成果，但不能把它标成 scoped accepted，也不能据此推进
`MODEL-INPUT-V2S` canon、G 或 formal 3200。
