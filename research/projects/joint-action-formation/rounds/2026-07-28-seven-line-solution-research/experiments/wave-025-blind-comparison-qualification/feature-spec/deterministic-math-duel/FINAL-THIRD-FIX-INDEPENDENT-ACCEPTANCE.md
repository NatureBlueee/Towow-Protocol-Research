# Deterministic-math V3 third-fix independent holdback

状态：**`REJECT_WITH_RETAINED_NUMERIC_SUBSCOPES` / NOT CANON / NO G / NO FORMAL 3200**  
日期：2026-08-01  
审查方式：读取 `THIRD-FIX-AUDIT.md` 后独立重放与扩展 holdback；未修改实现。

## 最终裁决

第三轮修复确实关闭了上一份报告的三个表面复现：普通 `None/int/bytes` pin 不再 raw crash，literal `NaN/Infinity/-Infinity` 与 metadata drift 被拒绝，`>8` 和 `1/3` 也不能再直接进入 family normalization。

但是本轮独立攻击发现新的、能够改变结果或逃逸 total failure contract 的绕过：

1. **恶意 `str` subclass 可以绕过 external SHA binding，令一个真实 SHA 完全不同、但结构合法的 1-ULP 表变异被接受。**
2. **合法 JSON exponent overflow、深嵌套 JSON 与 unpaired-surrogate metadata 仍会从 loader 泄漏 raw exception。** literal nonfinite token 的修复没有形成 strict JSON totality。
3. **family normalization 仍未冻结 producer input 的 container/leaf type。** 字符串容器 `"8"`、字符串 leaf `["8"]` 和 boolean leaf `[True]` 均返回 `OK`；`None` container、generator 与 scalar Fraction 则在 `try` 之前的 `len()` 泄漏 raw `TypeError`。

用户要求“任何新绕过都拒绝”，所以 V3 **不能获得 final wrapper acceptance**。数值边界 holdback 中通过的部分可以继续作为局部研究证据，不能抵消 binding 与 totality 失败。

## 冻结输入与基础重建

| 文件 | bytes | SHA-256 |
|---|---:|---|
| `deterministic_math_duel.py` | 64,734 | `04fc6150f3323688ee01a73a6fb5c0f3807aedfa3872493f9187e9c107147aa2` |
| `COUNT-LOG1P-BINARY64.candidate.json` | 12,870 | `0c91fac4170e278ff4e35b9c9ae026f749ffc326b9c94cc021c322d0993801d5` |
| `RESULTS.candidate.json` | 28,941 | `a9af8b9ea8e84b5c6f1f0d7dc1db9dd8e1e136e4e72c9721c71ee73ec5590787` |
| `tests/test_deterministic_math_duel.py` | 22,723 | `86d4d4e6ec90f3dbadfe456726b6948fae6dd09b5fe417464cd0498ce4cf2c32` |
| `README.md` | 9,354 | `5722b90a8b63223f9b3979625720001f8d9dd84825321e43a3be054a5f9cbaac` |
| `THIRD-FIX-AUDIT.md` | 3,623 | `0fd1be975a9ac4cdeb507d169de5fd5f0eed1864ce93d9c4bc05faabbb043598` |
| `FINAL-INDEPENDENT-ACCEPTANCE.md` | 12,792 | `d499f2ca509da78fce9a0e5a5431d83e1a37a446488b812da9601586463d312e` |

亲自执行：

- `RESULTS.candidate.json` canonical byte rebuild：PASS，28,941 bytes，SHA 与上表一致；
- tests：27/27 PASS；
- Python compile：PASS（使用 `/tmp` bytecode cache；默认用户 cache 路径被 workspace sandbox 拒绝，不是 source compile failure）。

27 个 tests 不能覆盖以下 holdback，因此不能用 green count 反驳本报告。

## External pin holdback

### 正常与普通错误输入

以下输入均稳定返回：

```text
NOT_QUALIFIED_TABLE_BINDING / TABLE_EXPECTED_SHA_GRAMMAR / controller_pin
```

- `None`、整数、`bytes`；
- 63/65 位；
- uppercase hex；
- fullwidth digits、accented character、newline、NUL、unpaired surrogate 等普通 `str`。

普通 built-in `str` 的 lowercase 64-hex grammar 已闭合，source/CLI 中也没有 SHA 默认值。

### H1 — `str` subclass 攻破真实 digest comparison

实现声称要求 “exact `str`”，实际条件是：

```python
isinstance(expected_sha256, str)
```

这会接受能覆写比较运算的 subclass。独立复现：

```python
class EvilPin(str):
    def __eq__(self, other): return True
    def __ne__(self, other): return False

pin = EvilPin("0" * 64)
```

然后把 frozen table 的 count=1 从：

```text
3fe62e42fefa39ef
```

合法地变异 1 ULP 为：

```text
3fe62e42fefa39ee
```

变异 raw 仍为 exactly 12,870 bytes，真实 SHA 为：

```text
b6a6f5c3addd4f71919c806dc2ef4b7081b34eb37747d5de1796572f06a81b2d
```

但传入 underlying text 为 64 个 `0` 的 `EvilPin` 后：

- regex 通过；
- `sha256(raw) != pin` 被 subclass 的 `__ne__` 改写为 `False`；
- loader 接受 1-ULP 变异；
- 对当前正常表，完全错误的同一 EvilPin 也让 `lookup_count_log1p(1, pin)` 返回 `OK`。

这是 external binding 的实质破坏，不是“错误类型只影响报错美观”。

修复门槛：至少要求 `type(expected_sha256) is str`，并在 comparison 前形成不可由 subclass 覆写的 built-in immutable value；修复后用同一恶意 subclass holdback 重放。

## Strict JSON / metadata holdback

### 已通过的部分

独立检查确认：

- literal `NaN`、`Infinity`、`-Infinity` 经 `parse_constant` 稳定拒绝；
- duplicate top/nested keys 经 object-pairs hook 稳定拒绝；
- top key set 必须完全相同；
- 六项 metadata 的普通 JSON type drift 和 exact-constant drift 稳定拒绝；
- entry count/index/duplicate、entry keys、16 lowercase hex 和 finite nonnegative range 仍闭合；
- `canonical_bytes` 对程序内部 nonfinite value 使用 `allow_nan=False`。

这些是正向的 structural subscopes，但不足以支持 “strict loader is total”。

### H2 — exponent overflow 绕过 `parse_constant`

JSON token `1e9999` 是合法 number syntax，不会触发 `parse_constant`。Python parser 把它转成 `float('inf')`。我把 `version` 换为 `1e9999`、调整另一个 metadata string 使 raw 保持 exactly 12,870 bytes，并提供真实 SHA。

实际结果不是 `TABLE_JSON` 或 `TABLE_METADATA`，而是从 canonical check 泄漏：

```text
ValueError: Out of range float values are not JSON compliant
```

原因是 `canonical_bytes(value)` 位于 loader 的 parse exception guard 之外。

### H3 — JSON nesting 与 surrogate 仍泄漏 raw exception

两个进一步的 exact-length、exact-SHA 变异：

- 以 1,000 层合法 JSON array 替换 metadata value，并缩小 entries / 填充其他 metadata 保持 12,870 bytes：raw `RecursionError`；
- 以 JSON escape `"\ud800"` 形成 unpaired-surrogate metadata，保持 12,870 bytes：canonical UTF-8 encode raw `UnicodeEncodeError`。

它们在 metadata exact-constant check 前逃逸，不返回冻结 failure code/stage/provenance。

修复门槛：所有 parse/canonical/depth/Unicode failure 必须包进 `TABLE_JSON` 或更窄稳定失败；增加明确 nesting/decode policy，并对 numeric overflow 使用 nonfinite parse rejection，而不仅是 literal constant hook。

## Family normalization holdback

### 数值边界实际通过

下表在 A/B 两条路径都符合第三轮声明：

| 输入 | 结果 |
|---|---|
| `8 + 2^-60`、`-8 - 2^-60` | `FAMILY_INPUT_CLIP_BOUND` |
| `1/3` | `FAMILY_INPUT_BINARY64_EXACT` |
| `8 - 2^-54`、`-8 + 2^-54`（在界内但不是 binary64 exact） | `FAMILY_INPUT_BINARY64_EXACT` |
| `2^-1075` | `FAMILY_INPUT_BINARY64_EXACT` |
| exact next-binary64 below `8` | `OK` |
| `+8`、`-8` | `OK` |
| minimum positive/negative subnormal | `OK`；A 的 square-round 路径归零，B 的 exact-dyadic 路径归一，符合两种故意不同的 study semantics |
| `Fraction(0)`、float `-0.0` | `OK` 且输出 canonical `+0` |
| leaf `None/object/complex/list/NaN/Infinity` | stable `LEAF_PARSE` domain failure |

因此 clip bound、binary64 exactness、minimum-subnormal 和 `+0` 的 **ordinary typed numeric subscopes 可以保留**。A/B 的 minimum-subnormal差异只说明定义不同，不选择正式算法。

### H4 — container 与 producer leaf type 没有冻结

wrapper signature 和说明声称消费 `Sequence[Fraction]` / post-parser rational producer，但以下输入返回 `OK`：

```python
evaluate_family_normalization("8", path)       # string 本身被当成一个 family
evaluate_family_normalization(["8"], path)     # raw numeric lexeme被 Fraction()重解析
evaluate_family_normalization([True], path)     # bool 被当作 exact 1
```

`[8]`、`[8.0]`、`["0.5"]`、`[Decimal("0.5")]` 也会被静默扩宽成 rational 并成功。后几项数值上恰好安全，但其接受集合没有被文档、schema 或 producer receipt 冻结；字符串尤其允许 raw lexeme 绕过“V2S upstream lexeme admission required”的边界。

另外，下列 malformed container 在 function 的 `try` 之前执行 `len(components)`，直接抛 raw `TypeError`：

```python
evaluate_family_normalization(None, path)
evaluate_family_normalization((x for x in [Fraction(1)]), path)
evaluate_family_normalization(Fraction(1), path)
```

所以第三轮只验证了 component numeric predicate，没有闭合 producer container/type contract，也没有使 family evaluator 成为总函数。

修复门槛：先明确且机器执行唯一输入类型。若正式边界是 post-parser `Fraction`，拒绝 `bool/str/float/Decimal` 和 string/scalar/generator containers；若允许其他表示，必须把允许集合、上游 lexeme admission谱系和 canonical conversion写入契约。所有 shape/type failure 都须在 `try` 内返回稳定 outcome。

## 证据边界复核

V3 没有把 wrapper 修复显式外推成下列结论；这些状态保持正确：

- rational→binary64：`SCOPED_ACCEPT_KERNEL_ONLY`；
- exact sqrt：`SCOPED_ACCEPT_KERNEL_ONLY`；
- log table correctly-rounded：`CORROBORATED_NOT_PROVEN`；
- wall-clock / CPU / peak RSS：`UNKNOWN / NOT_RUN`；
- formal reachability：`UNKNOWN`；
- task impact：`UNKNOWN`；
- minimal sufficient set：`UNKNOWN_NOT_CLAIMED`；
- G 与 formal 3200：`NOT_RUN`。

`path_b_wholesale_deletable=false` 仍只能解释为“现有 A/B adversarial cases 否定 universal byte equivalence”，不能解释为 B 实现已被选择或最小。

## 可继承与不可继承

可以继承：

- 第三轮对 ordinary built-in pin grammar、literal JSON constants、metadata constants 的局部修复；
- family 的 clip、binary64 exactness、subnormal 与 `+0` 数值 predicate；
- 前轮已经接受的 converter/sqrt kernel 和 ordinary typed numeric wrapper subscopes；
- study-only cap 与全部 `UNKNOWN` 边界。

不可继承：

- external SHA binding 已闭合；
- strict table loader 对有界 bytes 是总函数；
- family producer/consumer admission 已闭合；
- `raw_exception_allowed_from_total_evaluators=false`；
- 完整 deterministic-math wrapper package 已通过。

下一次复核必须以 H1–H4 为独立 holdback。修复前继续：**not canon / no G / no formal 3200**。

