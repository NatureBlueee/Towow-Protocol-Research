# Deterministic-math duel 独立红队

状态：**独立只读审查 / `NOT CANON` / `NO G` / `NO FORMAL 3200`**  
日期：2026-08-01  
审查对象：`feature-spec/deterministic-math-duel/` 的候选研究包；未读取模型、G 或 3200 population。

## 结论

| 有界主张 | 判定 |
|---|---|
| `rational_to_binary64_bits` 在无限精确 `Fraction` 输入上的 binary64 RN-ties-even 数学转换（含 midpoint、最大有限数、subnormal、underflow、规范化 `+0`） | **SCOPED ACCEPT**；独立 exact-neighbor oracle 8,882 次一致，但这不包含输入 admission、资源上限和失败码 |
| `exact_sqrt_to_binary64_bits` 对非负精确有理数的最后一次 binary64 舍入 | **SCOPED ACCEPT**；3,436 个 exact squared-midpoint cell 检查一致，但负值、溢出和资源失败仍没有总函数式契约 |
| A/B 五个记录到的 byte divergence 是真实算法语义差异，而不是 Python float 伪造的答案 | **SCOPED ACCEPT**；但它们不是五项独立机制，也尚未证明这些反例在未来正式输入域内可达或改变任务结果 |
| 256 项 frozen `log1p` 表的当前字节 | **CORROBORATED, NOT PROVEN**；Decimal 80/160/240 一致之外，独立 `/usr/bin/bc -l` 在 100/220 位也全部一致；仍无严格误差区间或正确舍入证明，发布绑定也未封闭 |
| type-7、`averaged_inverted_cdf`、raw/no-centering 的示例计算忠实性 | **SCOPED ACCEPT AS EXAMPLES**；不能据此选择 estimator 或 normalization，raw 也不是只替换 estimator 的同构对照 |
| “B 不可整体删除”这一 A-vs-B 二元比较结论 | **SCOPED ACCEPT**；存在真实不可 byte-equivalent 反例 |
| “当前最小组合”已经足以成为 `DETERMINISTIC-MATH` 候选或解锁 G | **REJECT**；缺少 admission、完整 operator/output-round 契约、failure vocabulary、资源封闭、发布锚、独立 provider 和真实成本/任务证据 |

因此，这个 duel 有研究价值：它成功排除了“固定顺序、每步 binary64 与 exact-last-round 总是等价”这个错误假设，也支持删除 bounded count transform 的运行时 transcendental。它还不是可接线的确定性数学规范，**不得解锁 G 或 3200**。

## 冻结输入

审查时的文件凭据：

| 文件 | bytes | SHA-256 |
|---|---:|---|
| `deterministic_math_duel.py` | 27,495 | `5394fd713668154b7070fa85a0c69b33acfa72aedfaa3f36189027fdffb84eb9` |
| `COUNT-LOG1P-BINARY64.candidate.json` | 12,870 | `0c91fac4170e278ff4e35b9c9ae026f749ffc326b9c94cc021c322d0993801d5` |
| `RESULTS.candidate.json` | 13,564 | `eea5dae1097e906700d796d23462ad0c2e1d3773659eb9bfc96e1740e5caf425` |
| `tests/test_deterministic_math_duel.py` | 7,542 | `4467384df9ec9860a4838d11809ffa0b07d3e6c12c3e06290912a81d1eec4a87` |

候选自检通过：`RESULTS.candidate.json` byte rebuild 一致，原有 15 tests 全部通过。这个结果只证明候选对自己已声明的例子一致，不被当作舍入正确性证明。

## 独立 KAT 与变异结果

### 1. rational → binary64

我没有使用 Python `float` 作为期望答案。独立 oracle 直接把每个有限 binary64 bit pattern 解释成精确有理数，在正数 bit 全序中二分相邻值，再用精确距离比较和低位奇偶决定 tie；最大有限数之上的邻点使用数学值 `2^1024`。

覆盖包括：

- `+0`、负数、负 underflow 规范化 `+0`；
- 最小 subnormal、最大 subnormal、最小 normal；
- normal/subnormal 两侧 midpoint 及 midpoint ± exact epsilon；
- 最大有限数、overflow midpoint 及两侧；
- 全 bit 区间随机相邻格和随机大整数/任意分母有理数。

结果：**8,882 / 8,882 一致**。这支持转换 kernel；没有覆盖 lexeme 长度/指数上限、内存耗尽或 infinity admission wrapper。

### 2. exact sqrt 最后舍入

独立检查不复用候选的“先找 lower 再比较 midpoint”返回逻辑，而是验证返回 bit 所属的完整正确舍入 cell：对相邻输出的 midpoint 平方建立精确上下边界，并按返回 bit 的偶数性检查 tie 包含方向。覆盖 `0`、subnormal、normal、最大有限数、overflow，以及随机 bit cell 和随机有理数平方。

结果：**3,436 / 3,436 一致**。特别地，zero/subnormal tie、normal midpoint tie 与 maximum-finite/overflow cell 均未发现错误。

### 3. frozen log1p 表

除了候选的 Python `Decimal.ln` 80/160/240 位检查，我用系统 `/usr/bin/bc -l` 分别在 `scale=100` 和 `scale=220` 重新计算 `ln(1+n)`，再经独立 exact-neighbor converter 转 binary64：

- 256 / 256 项在两个精度间稳定；
- 256 / 256 项与 frozen table bit 相同；
- disagreement = 0。

这增加了异质算法的佐证，但 `bc` 与 Decimal 都没有在这里产出包含真实值的严格上下区间，所以仍不能升级成“数学证明正确舍入”。当前表足够作为研究候选和未来 release KAT 输入，不足以自封为 release truth。

### 4. admission/failure 变异

以下都是当前实现的实际返回，不是推断：

| 变异 | 当前行为 | 所需语义 |
|---|---|---|
| A 累加 `2^1023 + 2^1023` | 返回 `+inf` bits，无失败码 | 必须在输出前转成冻结的 numeric-range failure |
| A 对最大有限分量求平方 norm | 后续把 infinity 转 Fraction 时抛 `ValueError` | 不应由调用路径决定 crash 形态 |
| B 对两个最大有限分量求 norm | 返回 `+inf` bits | 必须拒绝，不能进入矩阵 |
| A 的非零 exact scale 舍入为 `+0` | 抛无消息 `ZeroDivisionError` | 要区分 exact-zero、rounded-zero、underflow/range |
| B 的 exact zero scale | 抛无消息 `ZeroDivisionError` | 需要正式 failure code |
| B 累加 `[2^1024, -2^1024, 1]` | 因先精确抵消而返回 `1.0` | 若单叶必须先 admission，这是一条绕过路径 |
| negative sqrt | 抛 `ValueError("sqrt domain")` | 需要冻结 domain failure 与 provenance |

table loader 变异也发现：`bits_be_hex="-1"` 和 17 位 `"10000000000000000"` 都被 `load_table()` 接受；只有当前文件 digest 恰好阻止这些值出现在本研究结果里。发布 consumer 仍须检查恰好 16 位 lowercase hex、finite/允许范围和外部 pin。

## 五个 A/B 分叉是否成立

### 成立的部分

1. `2^53, 1, -2^53`：三项都是 exact binary64 dyadic。A 的逐步舍入确实丢失 `1`，B 的 multiset exact sum 为 `1`。调换次序后 A 改变、B 不变，真实暴露了 order-defined fold 与 mathematical multiset 的差别。
2. `1 + 1024 * 2^-60`：每一项也都是 exact binary64。A 把每个小项丢掉，B 的 exact sum 最后得到 `1 + 4 ulp`。这不是输入转换不对称。
3. `1` 加五个 `2^-27` 的 L2 norm：分量均可精确表示。A 每个小平方在累加时消失；B 的 exact squared sum 经正确舍入 sqrt 得到 `1 + 1 ulp`。差异成立。
4. `(2^53+1 - 2^53)/1`：差异成立，但它检验的是“decimal/rational preprocessing 是否在第一次 binary64 round 前执行”。`2^53+1` 本身不能表示为 binary64；如果权威输入已经先是 binary64，这个反例会消失。因此它只支持有该输入语义的 preprocessing claim。
5. `averaged_inverted_cdf` 示例：A 舍入 center/scale/中间除法，B 保持 exact rational 到最后一次 round，真实相差 1 ulp。它与第 4 项属于同一 broad semantic axis，不是第五种独立机制。

### 不能由这些分叉推出的部分

- 未冻结正式 model-input/admission，无法证明 `2^53`、1,025 个 collision terms 或这些 norm 维度在正式域内可达。
- byte divergence 不自动意味着预测、balanced accuracy 或实际任务发生变化。
- A 与 B 的二元 duel 不能证明 exact `Fraction` 实现是全局最小方案。固定宽 superaccumulator/Kulisch accumulator、canonical binned sum、整数缩放或其他可复现算法没有进入同约束比较。
- 所以“B 不可 wholesale delete”成立；“必须保留当前 B 的具体实现形态”不成立。

## quantile / centering 审查

- 候选 type-7 公式 `h=(n-1)p` 的四点结果 Q1=7.5、median=15、Q3=22.5 正确。
- `averaged_inverted_cdf` 的四点结果 Q1=5、median=15、Q3=25 正确。
- zero-IQR 时 scale=1，holdout `8` 相对 calibration 常量 `7` 保留为 `1.0`，与声明一致。
- `raw/no_centering/no_scaling` 忠实地计算了 raw control，但它同时删除 center 和 scale，不是只改变 quantile estimator 的单变量对照。
- `IQR / 1.349` 是被继承的设计选择，不由 deterministic math 决定；type-7、averaged、raw、zero-IQR policy 都仍需要同一真实任务 ablation。

因此示例没有偷换算术结果，但也没有给出 estimator 选择证据。

## “最小组合”尚缺的闭包

当前五条 retained mechanism 是合理的设计候选，不是已经证明的最小充分集。至少还缺：

1. **数值生命周期**：哪些输入先以 decimal rational 存活，哪些已经是 binary64 dyadic；每个 operator 后在哪一点 round；谁负责 nonfinite admission。
2. **division**：exact/rounded zero、极小 scale、负 scale、quotient overflow/underflow、最终 `+0` 规范化。
3. **clip/saturation**：count 的 `min(exact_count,255)` 只写在表 metadata，没有 executable admission；其他数值 clip 的先后顺序和边界未定义。
4. **normalization output**：center/IQR/scale 的校准样本域、round 点、holdout OOV/missing 与输出 range failure 未形成总函数。
5. **column/collision accumulation**：signed multiset、duplicate identity、固定序还是 exact sum 未绑定未来正式 routing；跨 family column aggregation 也未覆盖。
6. **norm**：空 family、非有限分量、平方和 overflow、输出 infinity、负输入和 provenance failure 未冻结。
7. **failure vocabulary**：当前混合了返回 infinity、`ValueError`、`ZeroDivisionError` 和 exact 抵消后成功；没有可跨 provider 比较的码、位置和 leaf provenance。
8. **资源封闭**：decimal digits/exponent、term count、Fraction numerator/denominator bits、quantile sample/sort、sqrt operand bits、table read bytes 都没有 executable cap。`O(n)` 没有包含 data-dependent bigint arithmetic complexity。
9. **发布绑定**：结果文件从当前 source/table 动态重建 hashes；同时修改 source、table、results 后仍可自洽。测试中的 table digest 不是 controller/external release pin，tests 也未被结果绑定。
10. **替代方案与任务证据**：尚未比较 exact Fraction 与可复现 superaccumulator/整数缩放等成熟实现，也没有任务 ablation。

## 成本真实性

`RESULTS.candidate.json` 只有渐进性文字：A 为 fixed-width `O(n)`，B 为 data-dependent big-integer `O(n)`。这不是成本测量，而且 B 的 `O(n)` 只计操作数，忽略了 numerator/denominator bit length、gcd、乘法和排序成本。

当前包没有：

- wall-clock、CPU、peak RSS 或 allocation 数据；
- 按 term count、decimal digits、denominator bits 的增长曲线；
- 两种 provider/语言的性能；
- 正式 3,200 population 上的成本；
- cap 命中后的失败成本。

因此成本状态是 **ESTIMATED ONLY**。本红队没有为了补一个漂亮数字而运行 3,200；那会越过当前 gate，也不能替代先冻结输入域和资源上限。

## 进入下一候选前的最小动作

1. 把已接受的 converter/sqrt kernel 与未接受的 admission/resource wrapper 分离登记，不能用前者的 KAT 给后者背书。
2. 先冻结每类值的权威表示和 round points，再决定 exact rational、exact dyadic 或 fixed binary64；用正式可达反例重跑 duel。
3. 用一个总函数式 evaluator 返回 `value | frozen_failure`，覆盖上述七个 admission 变异，禁止 raw exception 和 infinity matrix output。
4. 冻结并执行 digit/bit/term/sample/read ceilings，再测时间和内存；没有这些 cap，成本比较没有作用域。
5. frozen table 采用外部 release pin、严格 entry grammar、独立 holdback KAT；若要宣称“正确舍入”，再增加 rigorous interval 或可信 correctly-rounded provider，而不是把多精度稳定性改名为证明。
6. 在同一正式输入和成本约束下，至少加入一个 fixed-width exact/superaccumulator 类成熟替代，与当前 Fraction B 比较。
7. 完成两个 clean-room provider 的 byte rebuild 后，才讨论 `DETERMINISTIC-MATH` 候选；在此之前维持 **not canon / no G / no 3200**。

