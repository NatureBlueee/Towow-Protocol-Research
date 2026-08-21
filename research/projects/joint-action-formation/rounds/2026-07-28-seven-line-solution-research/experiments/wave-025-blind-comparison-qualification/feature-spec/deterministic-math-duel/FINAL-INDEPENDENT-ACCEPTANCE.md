# Deterministic-math V2 final independent acceptance

状态：**`PARTIAL_ACCEPT_SCOPED_WITH_BLOCKERS` / NOT CANON / NO G / NO FORMAL 3200**  
日期：2026-08-01  
审查方式：同一独立红队对 V2 做窄复核；读取了 `POST-FIX-AUDIT.md`，但所有结论均以当前实现和独立绕过重放为准。未修改实现。

## 总结判定

V2 已真实修复最危险的 numeric false-green：非法 leaf 不能再经 exact cancellation 洗白；sum、norm、sqrt、standardization 的常规 overflow/domain/zero-scale 路径已经从 infinity 或 raw exception 收敛为带 stage/provenance 的稳定失败；study-only 数值资源 cap 也确实执行。

但是 24 个回归以外仍存在三个最小绕过：

1. direct count total evaluator 对缺失或非字符串 external SHA 泄漏 raw `TypeError`；
2. 所谓 strict table grammar 接受 RFC JSON 不允许的 `NaN` metadata；
3. family normalization 没有执行它声明的 “already clipped finite binary64” 输入契约，因而 clip → family lifecycle 尚未形成可执行闭包。

因此本报告接受若干 **有前提的局部 wrapper**，但拒绝以下更强主张：

- `raw_exception_allowed_from_total_evaluators=false` 已对全部入口成立；
- table loader 的 strict JSON grammar 已闭合；
- column → standardize/clip → family normalization 已经由实现绑定；
- 当前 V2 是 `DETERMINISTIC-MATH` canon、G-ready 或 formal-3200-ready。

## 冻结审查输入与基础重放

| 文件 | bytes | SHA-256 |
|---|---:|---|
| `deterministic_math_duel.py` | 61,860 | `658bb71960d6f64b9fe3f43ae7496743e24198a99e22088789c1370afa52524f` |
| `COUNT-LOG1P-BINARY64.candidate.json` | 12,870 | `0c91fac4170e278ff4e35b9c9ae026f749ffc326b9c94cc021c322d0993801d5` |
| `RESULTS.candidate.json` | 27,312 | `51576f470f67fc3bb3bbf5515fbbedb4dd471e703f89700953115c7c1c10881e` |
| `tests/test_deterministic_math_duel.py` | 19,047 | `68aae77be16849b87459b74947b6e42124ad037687d3787bb05cc4d7878d3ee0` |
| `README.md` | 8,616 | `fb32f0c1f670990daf3e4b05f1a44bb9c48703009701d0c7da431ed1165b0fdc` |
| `POST-FIX-AUDIT.md` | 8,195 | `1478b38fcc7afcc668b8df754be7a2ecabd28981b14c94ee5365add3c57b13da` |

独立重放结果：

- 带外部 table SHA 的 `RESULTS.candidate.json` byte rebuild：PASS；
- 当前 24 tests：24/24 PASS；
- 前轮 converter 8,882 exact-neighbor checks 与 sqrt 3,436 exact-cell checks 没有被重跑成 wrapper 证据；其原作用域保持不变。

## Wrapper 逐项判定

| Wrapper / 层 | 最终窄判定 | 精确边界 |
|---|---|---|
| `admit_rational_leaf` | **ACCEPT_SCOPED** | 只对已经构造出的 post-parser `Fraction`；逐 leaf digit、binary exponent、finite binary64 range 和 `+0` 有效。原始 decimal lexeme/significand/exponent admission 仍必须由上游 V2S 完成 |
| `evaluate_column_accumulation` A/B | **ACCEPT_SCOPED** | 对声明的 typed sequence、最多 4,096 terms、unique raw UTF-8 identity 升序和上游 identity 大小约束；所有 leaf 在求和前 admission，B cancellation bypass 已关闭，A 每步 nonfinite 与 B intermediate/output 均 fail closed |
| `evaluate_sqrt` | **ACCEPT_SCOPED** | 对 typed post-parser rational；negative/domain、operand cap 和 output infinity 均返回稳定 failure。其 wrapper acceptance 不扩大 sqrt kernel 数学证据 |
| `evaluate_norm` A/B | **ACCEPT_SCOPED** | 对最多 4,096 个 admitted leaves；A square/add、B exact dyadic square/add、sqrt output 均有 range/cap gate；empty-family 是否业务允许仍由上层决定 |
| `evaluate_standardize` A/B | **ACCEPT_SCOPED** | value/center/scale/clip 四叶先 admission；exact zero、rounded-to-zero、negative scale 可区分；subtract/divide/clip/output round 与 `+0` 顺序可复现。estimator 和正式 clip policy 未被选择 |
| `evaluate_family_normalization` | **CONDITIONAL ONLY / PIPELINE CLOSURE REJECTED** | 数学 norm/divide 路径对普通 typed inputs稳定，但实现没有验证输入已 clip 且已经是 exact binary64 dyadic；只能在 controller 提供并验证此前置条件时局部使用 |
| `load_table_bytes` 的外部 digest binding | **ACCEPT_SCOPED** | source 内无 SHA 默认值；CLI `--check/--write-results` 必须由 caller 提供 SHA；单次 read 后校验 exact length + SHA，未发现 self-sync 路径。成立依赖 external controller pin 本身是可信输入 |
| `load_table_bytes` 的 strict structure/JSON grammar | **REJECTED PENDING FIX** | entry count/index/duplicate/key/16-lowercase-hex/finite-positive checks有效，但 Python JSON 的 non-finite constants仍可绕过 metadata grammar |
| `lookup_count_log1p` | **DATA PATH ACCEPT_SCOPED, TOTALITY REJECTED** | 对合法 `str` external pin 和 exact non-bool u64 count，`min(count,255)`、lookup、finite 与 `+0` 正确；缺失/错误类型 pin 会泄漏 raw exception |
| `robust_parameters` / quantile helpers | **STUDY HELPER ONLY** | leaf/sample/intermediate cap 可执行；它不是 outcome-shaped total evaluator，estimator、IQR/1.349、raw/no-center 的选择仍未验证 |

## 独立重放：已修复路径

### 1. 每 leaf admission 与 cancellation bypass

`[2^1024, -2^1024, 1]` 在 B column 求任何 exact sum 之前，于 `term[0]/term-0000` 返回：

```text
NOT_QUALIFIED_NUMERIC_RANGE / LEAF_RANGE
```

同样的“先完成全部 admission，再组合”结构存在于 norm、standardization 和 quantile calibration。family normalization 会先经过 `evaluate_norm` 的完整 admission；没有发现 ordinary typed Fraction 输入通过 cancellation 绕过 leaf range 的路径。

### 2. nonfinite、raw exception、zero/underflow scale

以下旧绕过均已在 total numeric wrappers 中关闭：

- A column add overflow → `COLUMN_ADD / NOT_QUALIFIED_NUMERIC_RANGE`；
- A norm square overflow → `NORM_SQUARE / NOT_QUALIFIED_NUMERIC_RANGE`；
- B norm sqrt output overflow → `NORM_SQRT / NOT_QUALIFIED_NUMERIC_RANGE`；
- negative sqrt → `SQRT_DOMAIN / NOT_QUALIFIED_NUMERIC_DOMAIN`；
- exact-zero scale → `SCALE / NOT_QUALIFIED_NUMERIC_SCALE_ZERO`；
- finite exact scale round-to-zero → `SCALE_ROUND / NOT_QUALIFIED_NUMERIC_SCALE_UNDERFLOW`；
- negative scale → `SCALE / NOT_QUALIFIED_NUMERIC_DOMAIN`；
- input float NaN/inf → leaf parse domain failure。

这些结果接受的是 wrapper 的 ordinary typed numeric domain；旧 `path_a_*` / `path_b_*` raw kernels 仍可能返回 infinity 或抛异常，只能用于已有 scoped duel/KAT，不能成为 matrix producer。

### 3. sum / norm / division / clip / `+0`

- column A 使用 frozen identity order 且每 add round；B 在 cap 下 exact add、最后一次 round；duplicate、倒序和 lone surrogate identity 均 fail closed；
- norm A 的 multiply/add 各自检查 nonfinite；B 将 admitted binary64 component 作为 exact dyadic，再检查 square/sum cap 和最终 sqrt；
- standardization A 与 B 的 subtract/divide round point不同但已明确；两者都在声明位置 clip 到 `[-8,8]` 并规范化 zero；
- zero family 不执行 division，输出 norm `+0` 以及每 component `+0`；
- nonzero family 除以 rounded norm，最终输出再次检查 nonfinite 并规范化 `+0`。

这些局部算子次序是可复现的。它们不选择 A 或 B，也不证明全 pipeline 的输入谱系已经被强制执行。

### 4. study resource caps

下列研究护栏确实执行：

- numerator/denominator 各 4,864 decimal digits；
- post-parser rational absolute binary exponent 14,000；
- sum/norm terms 4,096；quantile samples 4,096；
- exact intermediate numerator/denominator 各 16,384 bits；
- table read 先受 16,384 bytes cap，再要求当前 exact 12,870 bytes。

4097 terms、4865-digit leaf、binary exponent越界以及约 9,000-bit 互异分母相加导致的 intermediate cap 均稳定失败。

边界仍然诚实但重要：Fraction 构造前的 lexeme 资源、identity bytes/provenance 大小、正式可达分布和正式 cap 都不在本 wrapper 内。当前 cap 只能 **ACCEPT AS STUDY GUARDS**，不能冒充 production/formal resource closure。

## 三个剩余最小绕过

### B1 — external pin 类型错误逃逸 raw exception

下列 direct total-evaluator 调用实际抛出 `TypeError`，没有返回 `NOT_QUALIFIED_TABLE_BINDING`：

```python
lookup_count_log1p(1, None)
lookup_count_log1p(1, 7)
lookup_count_log1p(1, b"0" * 64)
```

根因是 `load_table_bytes` 在检查 `expected_sha256` 是否为 `str` 前，直接把它传入 string regex。CLI 对“参数完全缺失”有 parser gate，但 direct evaluator API 和非字符串 caller 没有。

这不构成 self-sync；source 内确实没有默认 SHA。它构成的是 totality/failure-contract 反例。修复要求先做 exact type + 64 lowercase hex admission，并统一返回 `TABLE_EXPECTED_SHA_GRAMMAR / controller_pin`。

### B2 — strict table grammar 接受 `NaN` metadata

独立变异步骤：

1. 保留 256 entries 完全不变；
2. 把 top-level `version` 改成 Python `NaN`；
3. 给另一个 metadata string 增加 4 bytes，使 canonical encoder 输出仍为 exactly 12,870 bytes；
4. 由 external caller 提供这些实际 bytes 的正确 SHA。

`load_table_bytes` 返回成功，并解析出 `version_is_nan=true`。同样的变异对 `candidate_status`、`construction_source`、`runtime_rule`、`schema`、`serialization` 都成功。

根因是 Python `json.loads` 默认接受 `NaN/Infinity`，`json.dumps` 默认也会生成 `NaN`；closed key set 并未验证 metadata type/value。外部 SHA 能证明“收到的是 caller pin 的 bytes”，不能把非 JSON 变成 strict JSON。

修复至少需要 parser `parse_constant` fail closed、encoder `allow_nan=False`，并冻结 metadata exact type；若这些 metadata 参与语义，还应冻结 exact value或由外部 manifest单独绑定。

### B3 — family normalization 的 clipped/binary64 前提未执行

两条普通 typed Fraction 反例在 A/B 都返回 `status=OK`：

```python
evaluate_family_normalization([Fraction(100), Fraction(0)], path)
evaluate_family_normalization([Fraction(1, 3)], path)
```

第一条绕过声明的 `[-8,8]` clip 前提，norm 仍按 100 计算并输出 `[1,0]`；第二条不是 exact binary64 dyadic，却被 wrapper 静默 leaf-round，然后以 “already-clipped column values” lifecycle 返回成功。

因此 `evaluate_family_normalization` 的数学结果本身可以有界使用，但不能证明 clip → family 的 producer/consumer 连接正确。修复可选：

- 接受 binary64 bits 而不是 arbitrary Fraction；并验证每 component finite、`abs <= CLIP_ABS`；或
- 绑定并核验由 standardization/column producer 产生的 typed receipt/preimage，而不是仅靠调用约定。

## External SHA、table 与证据边界

正向结论：

- source 中没有 authoritative/default SHA；
- CLI 的 check/write 缺少 `--expected-table-sha256` 会拒绝；
- loader 对当前 exact raw bytes 做 single-read length + SHA check；
- duplicate JSON key、entry duplicate/index错位、extra keys、负/大写/17位/nonfinite/sign-bit hex 均已拒绝。

仍需保持：

- 可信性来自 controller/reviewer 的 external pin，而不是 result 内回显的 SHA；
- 当前 table 数值只有 Decimal + `bc` 多精度一致，状态仍是 **`CORROBORATED_NOT_PROVEN`**；
- 任何 wrapper 修复都不能把它升级为 correctly-rounded transcendental proof。

## Kernel 证据没有被外围借用

V2 result 把 converter 与 sqrt 登记为 `SCOPED_ACCEPT_KERNEL_ONLY`，并明确“不提升 wrappers 或 G readiness”。README 和 post-fix audit 也保留了相同边界。没有发现把 8,882 / 3,436 检查改写成 admission、resource、pipeline 或正式任务证据的文字路径。

对应结论继续保持：

- rational→binary64 kernel：`SCOPED_ACCEPT_KERNEL_ONLY`；
- exact sqrt kernel：`SCOPED_ACCEPT_KERNEL_ONLY`；
- table correctly rounded：`CORROBORATED_NOT_PROVEN`；
- wall-clock / CPU / peak RSS：`UNKNOWN / NOT_RUN`；
- formal reachability：`UNKNOWN`；
- task impact：`UNKNOWN`；
- minimal sufficient set：`UNKNOWN_NOT_CLAIMED`。

## 最终门禁

当前允许继承的只有本报告表格中的局部结论。要把 V2 wrapper package 升到完整 `ACCEPT_SCOPED`，至少需要：

1. pin type/grammar fail closed，direct lookup 不再泄漏 raw exception；
2. JSON non-finite constants fail closed，并补 top metadata type/value grammar；
3. family normalization 机器验证 finite binary64 + clip bound，或绑定可信 producer receipt；
4. 重放三条 holdback bypass，并由独立审查确认；
5. 保持原有 24 tests、result byte rebuild 与既有 kernel evidence 边界不变。

在这些动作完成前：**not canon / no G / no formal 3200**。
