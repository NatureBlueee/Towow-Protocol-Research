# Wave025 C01 minisuite 独立红队

> 审查对象：`feature-spec/model-input-c01-minisuite/` 当前候选字节  
> 审查方式：不修改实现；独立重跑、逐项重算、最小反例和来源边界核对  
> 审查结论：`REJECT_AS_EXECUTABLE_C01_SEMANTICS`；保留一部分合成机制判别结果  
> 本文不是 `MODEL-INPUT-V2S` canon，不是 D0/D1 功效证据，不授权 G 或 3200。

## 1. 结论

当前包不是“全错”。在它**自己实现的语义**下，四份 JSON 可以由当前代码逐字节重生，
balanced accuracy、预测类 support 下界和 family 内的确定性排序也能够复算；P4/F2、P5/F3
确实构成了清楚的小机制判别，P3/P7 保留了有价值的负结果。

但它还不能用来冻结 C01，原因不是现实功效尚未运行这一项外部 Unknown，而是至少五个内部
语义/证据缺口：

1. holdout labels 在规则选择**之前**已经 join 并驻留于同一调用栈；`before_holdout` 和
   `holdout_reselection_attempted=false` 只是结果字段，不是冻结边界；
2. 所谓“无 label 的 feature fixture”在 `row_id` 和 token bytes 中直接写有 `R/S`、
   `role-r/role-s`，现有 label-blind test 是同一输入调用同一纯函数的恒等式；
3. F4 实现的是完整 `00/01/10/11 -> class` 二位查表，不是已绑定 `FEATURE-SPEC.json` 写的
   `two_token_conjunction`；P6 的 XOR 成功依赖这个语义替换；
4. `stable_recovery` 只检查 holdout，而已绑定 feature spec 要求 calibration 与 holdout
   两阶段、两类 recall 都为 1；
5. README 声称 OOV 固定 fallback 为 R，但 F1 对 OOV-only row 走 `absent_class`，该类可以是 S。

另有一个来源边界问题：P1 的 role-stable exact atom 可以追到公开 D0 设计；公开 D1 family
registration 只写了 role-correlated current-run canary，并没有写“一值/role 且跨 phase 复用”。
当前 private preformal registry 确实含这个稳定性条件，但它未绑定、D1 还复用已 reveal 材料，且本包
明确声称未把 private registry 当输入。因此 P2 可以是**条件性机制类比**，不能表述成已由当前
公开绑定来源推出的 D1 设计事实。

综上，当前适当状态是：

| 判断层 | 状态 | 可保留结论 |
|---|---|---|
| 合成机制判别 | `PARTIAL_ACCEPT` | P3/P4/P5/P7 与 F1 对 opaque stable atom 的兼容性有信息量；P6 只证明二位查表，不证明 strict conjunction |
| 当前 D0/D1 功效 | `UNKNOWN / NOT_RUN` | P1 对 D0 是机制类比；P2 仍缺公开稳定性绑定；两者都没有 actual V2S receipt |
| `MODEL-INPUT-V2S` canon | `REJECTED / NOT_A_CANDIDATE` | 尚未形成唯一 C01 机器语义和可审计 phase boundary |
| G | `NOT_RUN / NOT_UNLOCKED` | 本包不能解除 G 前置条件 |
| 3200 formal | `NOT_RUN / FORBIDDEN_TO_INFER` | 无实际功效、CI、T role-null 或资源结果 |

## 2. 独立复现

执行：

```text
python3 c01_minisuite.py --check
=> byte-exact canonical check passed: 4 artifacts

python3 -m pytest -q tests
=> 13 passed
```

当前字节：

| 文件 | bytes | SHA-256 |
|---|---:|---|
| `C01-MINISUITE-CONTRACT.candidate.json` | 1,817 | `34ae4de21d694c67280faaace3f6eaa956f8f6aa3670be99d666eae1f9cb5f3b` |
| `CASES-FEATURES.candidate.json` | 90,860 | `26ce417644c294223dc000a177cfb45c880e6c54d5a050d78ec229013a06a2c5` |
| `CASES-LABELS.candidate.json` | 36,704 | `e08f91e2c20d47ea8a5c181ba5d142219209b7048be7a4b686d8e32a999ef266` |
| `RESULTS.candidate.json` | 152,222 | `7c7d6c368ce662219e832d9b4ccdab5d5325063541429321feee430194808994` |
| `c01_minisuite.py` | 30,413 | `1ac6d677839c21672b89bded9ca48020880bb972375062a48f6f4c8958cdc300` |
| `tests/test_c01_minisuite.py` | 9,439 | `dada0b26b2b1f0c16812ea3372aab72b137c4670e226ff04a918bcf15d8e59be` |
| `README.md` | 4,634 | `d968fcaa228427499df689e66d320a8357c7c6431345e16090ff948d8675ae6b` |

`RESULTS` 内的 contract/features/labels 三个 binding 与当前 canonical bytes 相符；两个公开外部
source hash 也都相符，且 public registration 内绑定的 `FEATURE-SPEC.json` hash 仍等于当前文件。

这只证明“当前 checkout 可由当前 generator 重建当前 JSON”。`RESULTS` 没有绑定 generator、tests、
README 或一次独立执行 receipt，所以它不是能够脱离当前可变工作区验证的完整生成谱系。

## 3. 发现一：holdout 不是先冻结后 reveal

`evaluate_case` 的实际顺序是：

```text
freeze calibration universe
join calibration labels
join holdout labels
select calibration rule
hash alleged before-holdout rule
score holdout
```

独立运行时在第一次 `select_rule` 入口检查调用者局部状态，已经观察到：

```text
joined_holdout length = 40
joined_holdout labels = [R, S]
```

也就是说，`rule_sha256_before_holdout` 实际产生在 holdout label join **之后**。当前实现确实只把
`joined_calibration` 作为显式参数传给 `select_rule`，所以源代码审阅尚未发现当前结果的直接重选；
但这不是合同声称的独立 phase boundary。`holdout_reselection_attempted: false` 是硬编码常量，
before/after hash 也只证明同一 Python object 在评分前后没变，不能证明选择器当时不可读 holdout。

这属于内部可修复 blocker，不应归为“真实运行以后再验证”。冻结规则、预测、rule bytes/sha 和
prediction manifest 必须先完成；随后另一个只接收冻结产物的步骤才 join holdout labels 和评分。

## 4. 发现二：feature fixture 不是语义上的 label-free

`contains_labels=false` 和“不存在键名 `label`”只检查了 JSON 形状。生成器实际使用：

```text
row_id = <case>-<phase>-R/S-<index>
P1 token = synthetic-d0-role-r/s-stable
P2 token = synthetic-d1-role-r/s-stable
P3 token = <phase>-R/S-<index>
```

当前 features bytes 中，`-R-` 与 `-S-` 各出现 320 次，`role-r-stable` 与 `role-s-stable` 各出现
80 次。universe builder 当前没有解析这些字符串，所以这没有直接改变这一次候选选择；但它使
“builder 输入无 role”与“feature fixture 不含 label”的审计主张不成立，也让现有完整 label inversion
test 退化成对同一 `freeze_universe(calibration)` 连续调用两次。

独立把 P1 row IDs 改成不含 role 的连续 opaque ID，并把两个 token 改成不含 R/S 的 opaque atom，
F1 的 calibration/holdout balanced accuracy 仍为 1、stable 仍为 true。因此 P1 的窄机制结论不依赖
这些明文标签；应当清除它们并加入实际的 byte-level noninterference / permutation test，而不是把
这个缺口解释为合成任务必须如此。

## 5. 发现三：F4 用二位查表替换了 conjunction

当前绑定 `FEATURE-SPEC.json` 的 C01 第四 family 名为：

```text
two_token_conjunction_from_TOP256_CALIBRATION_SUPPORT_TOKENS
```

minisuite 却为每个 pair 学习所有已观察 `00/01/10/11` state 的多数类 mapping。P6 选中的规则是：

```json
{"00":"R","01":"S","10":"S","11":"R"}
```

这正是 XOR lookup。独立把 family 限定为一个普通 `A AND B` predicate（允许正负 class orientation）
后，P6 最佳 holdout balanced accuracy 只有 `0.75`，R/S recall 为 `0.5/1.0`，达不到 stable recovery。

所以 P6 确实区分了“单一 AND conjunction”和“完整二位 Boolean-state mapping”，但当前包先选择
了后者，再把结果写成 F4 胜出。它没有回答原本需要决定的问题。二位查表可能是合理的成熟机制，
也可能比单 conjunction 更合适；需要明确采用并更新作用域/复杂度，而不能把它说成既有
conjunction 的机械实现。

## 6. 发现四：stable recovery 少了 calibration 条件

当前 `stable_recovery_exact_both_classes` 只检查 holdout recall。最小变异：

- calibration：一个 F1 token 对 R/S 都有噪声，最佳规则 BA=`0.75`，预测 support=`20/20`；
- holdout：同一规则恰好完美，BA=`1.0`。

当前 evaluator 返回：

```text
stable_recovery_exact_both_classes = true
```

但当前绑定 feature spec 定义的是同一冻结规则在 calibration **和** holdout 两阶段、两类 recall
均为 1。当前七个 case 的胜者恰好也都 calibration perfect，因此已列胜者没有因这个 bug 立即改变；
不过 evaluator 可以把未来非完美 calibration 规则错误升格为 stable，必须在进入 canon 前修复。

## 7. 发现五：F1 的 OOV 不总是 fallback R

README 说“无 eligible rule、未见 mapping state 和 OOV 的固定 fallback 都是 R”。F2/F3 的未见 state
确实用 `oov_fallback_class=R`；F4 对未见 Boolean state 也如此。F1 没有 OOV branch：只检查 selector
presence，然后走 `present_class/absent_class`。

独立最小变异中，calibration 的 R 行含已知 token、S 行为空，选中规则为：

```text
present_class=R, absent_class=S
```

holdout 行只含一个从未见过的 token；`oov_count=1`，但预测是 `S`，不是 `R`。这不一定说明正确
设计必须把该行判 R；它说明当前合同同时宣称了两个不兼容的行为。需要明确 F1 的推理对象究竟是
“冻结 selector 的 presence/absence”（则未知无关 token 不触发 OOV fallback），还是“row 含任何
universe 外 exact atom 就整体 fallback”。

## 8. support、BA、tie、MISSING 的通过项与边界

### 8.1 通过项

- balanced accuracy 由 `Fraction` 的两类 recall 平均计算；当前结果中的 numerator/denominator 可复算；
- `predicted_class_support` 是规则对 calibration 每个预测类的 row 数，不是正确数；
- 边界攻击 `R=5,S=5` eligible，`R=4,S=6` rejected，当前实现忠实执行了本包写明的 `>=10 total`
  和 `>=5 each predicted class`；
- top-256 是 calibration row-presence support 降序，再按 canonical identity bytes 排序；不接收 labels；
- F2/F3 显式保留 `MISSING`，P7 的未见 `COUNT:3` 使用冻结 R fallback，没有重新扩 universe；
- 每个 family 内先按 calibration BA、complexity units、最终 canonical JSON bytes 确定性选择。

### 8.2 仍需限定

- 所有当前规则都无 abstention、总会预测每一行，所以“total support”实际上等于 calibration 行数，
  对候选没有额外筛选力；这是本包的自洽解释，不自动证明它就是原 C01 所称 support 的唯一解释；
- 当前只在 family 内选择，没有执行四个 family 的统一候选池选择。`F1 是最简单充分子集` 是基于
  P1/P2 的人工比较，不是跨 family selector 的输出；
- complexity units 是本包新定义，尚未由绑定来源唯一确定；
- tie 使用的是加入自绑定字段后的整个 frozen rule JSON。它确定，但若 canon 想按语义字段 bytes
  tie，必须明确 hash/length 元数据是否参与排序。

## 9. P1/P2 与当前 control 的精确关系

### P1 / D0

公开 D0 design 明确写有：两个 role 各一个不同 16-byte CSPRNG tag、每个 role 的值跨
calibration/holdout 复用、主路径是 CWD entry exact path。因此 P1 正确捕捉了“一个 role-stable
exact atom 能被 F1 calibration dictionary 再命中”的机制核心。

它仍然只是 20/role/phase 的理想合成任务；没有实际 V2S path、receipt、opaque registry binding、
ablation、T zero-ingress 或正式 50/role/phase 数据。

### P2 / D1

当前 public registration 绑定 family、F07、current-run role-correlated canary 和 C01 primary，
但没有绑定 one-token-per-role/cross-phase-stable。当前 private preformal registry 提供该稳定性，
同时状态是 `NOT_BOUND` 且 D1 材料是已 reveal smoke 的复用。因此：

- “若 D1 每 role 一个 opaque atom 跨 phase 复用，则 F1 机制兼容”可保留；
- “当前公开 D1 设计已经证明满足这个前提”不可由本包现有 source bindings推出；
- actual D1 功效仍是 Unknown。

## 10. 最小修复门槛

这不是要求扩大 C01，而是把本包已声称的窄边界做真：

1. 将 feature row IDs 与 token 全部改成不泄露 role/class 的 opaque bytes，并加入真实的 role
   permutation/noninterference test；
2. 在 holdout labels 不可读的阶段冻结并落盘 universe、rule、predictions 与 hashes，再由独立评分
   步骤 join holdout labels；禁止用布尔字段自证 no-reselection；
3. 对 F4 作出明确选择：strict conjunction、带 negation 的单 pattern，或完整 2-bit mapping；名称、
   complexity、P6 预期和绑定 spec 必须一致；
4. stable recovery 同时检查 calibration 与 holdout 两阶段、两类 recall=1；
5. 明确 F1 在 OOV-only/unknown-plus-known row 上是 absence semantics 还是整体 fallback；补最小真值表；
6. 若 P2 继续称为当前 D1 analogue，绑定一个不暴露 private value、但能证明 one-per-role 与
   cross-phase stability 的公开结构性 manifest；
7. 在结果中绑定 generator/test/contract 版本和独立运行 receipt，或把可重建性主张限定为
   “当前 checkout 自检通过”。

修复这些内部项后，这个 minisuite可以成为选择 C01 最小语义的有用局部工具；即使如此，它仍只
回答合成机制可区分性，不会自动变成实际 D0/D1 sensitivity、MODEL-INPUT canon、G 通过或 3200
formal 证据。
