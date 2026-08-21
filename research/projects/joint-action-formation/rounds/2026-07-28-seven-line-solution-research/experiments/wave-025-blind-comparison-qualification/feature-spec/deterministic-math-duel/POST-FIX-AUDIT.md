# Deterministic-math duel V2 post-fix audit

状态：**窄修复完成 / 等待同一独立审查者复核 / NOT CANON / NO G / NO FORMAL 3200**  
日期：2026-08-01

## 修复对象与不变边界

本轮只修复 `INDEPENDENT-REDTEAM.md` 指出的 admission、failure、资源、发布绑定和数值生命周期
假绿路径，没有把 duel 改写成正式 `DETERMINISTIC-MATH`，也没有保留“当前组合已经最小充分”或
“可以解锁 G”的结论。

保留的正向证据仍严格有界：

- rational→binary64 kernel 的 8,882 次独立 exact-neighbor 一致是
  `SCOPED_ACCEPT_KERNEL_ONLY`；
- exact sqrt kernel 的 3,436 次独立 exact-cell 一致是
  `SCOPED_ACCEPT_KERNEL_ONLY`；
- Decimal 与异质 `/usr/bin/bc -l` 的 256 项表一致只是
  `CORROBORATED_NOT_PROVEN`，没有改名成正确舍入证明；
- A/B 的 5 个分叉是 5 个 case、约 3 个 broad semantic axis，不是 5 项独立机制；其 formal
  reachability 和 task impact 都是 `UNKNOWN`。

## 红队问题到 V2 修复

| 红队问题 | V2 动作 | 可执行回归/结果 | 当前边界 |
|---|---|---|---|
| B 可用 exact cancellation 洗掉非法 leaf | column sum、norm、standardization、quantile、family normalization 都先逐 leaf admission，再做任何组合 | `[2^1024,-2^1024,1]` 在 `term[0] / LEAF_RANGE` 返回 `NOT_QUALIFIED_NUMERIC_RANGE` | post-parser rational 无法重建原始 number lexeme；上游 V2S lexeme admission 仍是必需依赖 |
| A sum 返回 inf；A norm 后续 crash；B norm 返回 inf | total evaluator 在 leaf、每步 A op、B output round、sqrt output 全部拒绝 nonfinite | A sum overflow=`COLUMN_ADD`；A max norm=`NORM_SQUARE`；B two-max norm=`NORM_SQRT`，统一 range code | raw mathematical kernels仍可返回 conversion bits，只允许用于 scoped KAT，不能直接写 matrix |
| scale zero/underflow/negative 产生 raw exception | scale 精确零、非零但 round-to-zero、负 scale 分开为稳定 failure；所有 A/B standardization 走统一 outcome | `NUMERIC_SCALE_ZERO`、`NUMERIC_SCALE_UNDERFLOW`、`NUMERIC_DOMAIN` 均有 A/B regression | formal scale estimator仍未选择 |
| negative sqrt 抛 `ValueError` | `evaluate_sqrt` 先 admission，再返回 domain failure、stage、provenance | `negative_fixture / SQRT_DOMAIN / NOT_QUALIFIED_NUMERIC_DOMAIN` | sqrt kernel 对负数本来无数学值；修的是 wrapper 总函数性，不是 kernel 主张 |
| exact B 无资源闭包 | study-only term、digit、binary exponent、intermediate bits、quantile sample、table byte caps全部执行；每个正例记录 operation count/peak Fraction bits | term 4097、4865-digit leaf、binary exponent越界、两个约 9000-bit 分母的中间 lcm 都 fail closed | caps 是研究护栏，不是正式输入域；wall/CPU/RSS与正式 3200 成本仍 `UNKNOWN` |
| table 接受负 hex、17 位、index/duplicate/extra，且 digest可自洽改写 | loader无内部digest默认值，必须接收caller/controller外部 expected SHA与 exact length；再检查 duplicate JSON key、canonical bytes、closed top/entry keys、256 entries、canonical count/index/unique、恰好16位 lowercase finite nonnegative bits | negative/uppercase/17位/inf、duplicate count/key、swapped index、top/entry extra、SHA mutation均拒绝 | table正确舍入仍未被严格区间证明；release authority仍未建立 |
| count clip只存在 metadata | `lookup_count_log1p` 执行 exact u64 admission→`min(count,255)`→pinned lookup→+0 | 0、1、255、256及负数/u64 overflow均有回归 | 只覆盖 bounded count transform |
| column accumulation未闭合 | 要求 unique raw UTF-8 identity严格升序；每叶 admission；A每步round，B exact under caps最后round；所有zero输出规范+0 | unsorted、duplicate、lone surrogate、signed cancellation、many-small+large均有回归 | future routing是否要 multiset或order-fold仍 `UNKNOWN` |
| division、clip、norm order未闭合 | standardization冻结 A/B各自 subtract/divide round point，再统一 clip `[-8,8]` 与+0；family normalization只消费已clip列，norm=0不除，非零除以rounded norm后output-round | value 100→8、zero family全+0、3/4 family norm=5、finite normalized components | type-7/averaged/raw、IQR/1.349与normalization on/off仍需任务ablation |
| “最小组合”越过证据 | 从 machine result 与 README 删除 `smallest_retained_mechanism`，改为 `minimal_sufficient_set=UNKNOWN_NOT_CLAIMED` | result同时登记 superaccumulator/binned/scaled-integer 未比较 | 只保留“universal A/B byte equivalence被反例否定” |

## V2 数值生命周期

### Column

`strict identity order → independent leaf admission → A per-add round | B capped exact-add → finite output round → +0`

同 identity 重复不被悄悄相加；它必须在上游完成已声明的 category occurrence aggregation。column
evaluator只接受严格唯一的 source identity 序列。

### Numeric standardization

- A：`leaf admission → leaf round → subtract+round → divide+round → reject nonfinite → clip[-8,8] → +0`
- B：`leaf admission → exact subtract/divide under cap → exact clip[-8,8] → one output round → +0`

这两个路径仍故意计算不同函数；V2 只把各自 round/clip/failure位置写成可复现总函数，不判定谁是正式答案。

### Family normalization

输入是已完成 column accumulation 和 numeric clip 的有限 binary64 components。先以各路径计算 bounded
norm；norm=0 时所有 component和 norm列均为 canonical +0；norm>0 时用 rounded norm逐 component
division、output round、nonfinite rejection与+0 canonicalization。

### Count

`exact u64 admission → saturated=min(count,255) → externally pinned table lookup → finite check → +0`

## 资源与成本诚实性

V2 executable study guards：

- canonical numerator/denominator：各最多 4,864 decimal digits；
- post-parser rational absolute binary exponent：14,000；
- sum/norm terms：4,096；quantile samples：4,096；
- exact intermediate numerator/denominator：各 16,384 bits；
- table：最大 16,384 bytes，当前还要求 exact 12,870-byte pin。

上游 V2S `abs decimal exponent <= 4096` 仍必须在原始 lexeme admission 执行；post-parser Fraction不能
反推其文本长度、significand或exponent写法。当前结果只测了每个 fixture 的 exact operation count和
peak intermediate bit length。wall-clock、CPU、peak RSS、正式 3,200 与正式可达分布没有运行，状态是
`UNKNOWN / NOT_RUN`。

## 回归与凭据

执行：

```bash
python3 deterministic_math_duel.py --expected-table-sha256 0c91fac4170e278ff4e35b9c9ae026f749ffc326b9c94cc021c322d0993801d5 --check RESULTS.candidate.json
python3 -m unittest discover -s tests -v
```

结果：`24/24` tests通过，result byte rebuild一致。

| 文件 | bytes | SHA-256 |
|---|---:|---|
| `deterministic_math_duel.py` | 61,860 | `658bb71960d6f64b9fe3f43ae7496743e24198a99e22088789c1370afa52524f` |
| `COUNT-LOG1P-BINARY64.candidate.json` | 12,870 | `0c91fac4170e278ff4e35b9c9ae026f749ffc326b9c94cc021c322d0993801d5` |
| `RESULTS.candidate.json` | 27,312 | `51576f470f67fc3bb3bbf5515fbbedb4dd471e703f89700953115c7c1c10881e` |
| `tests/test_deterministic_math_duel.py` | 19,047 | `68aae77be16849b87459b74947b6e42124ad037687d3787bb05cc4d7878d3ee0` |
| `README.md` | 8,616 | `fb32f0c1f670990daf3e4b05f1a44bb9c48703009701d0c7da431ed1165b0fdc` |
| `INDEPENDENT-REDTEAM.md` | 12,505 | `12168b9f52090b907a5e2e83f4aed5b43c4c609be958c75d0a576151a45ce8dc` |

## 待同一审查者复核的窄问题

1. 每个 total evaluator 是否还存在 raw exception、inf/NaN success或cancellation-before-admission路径；
2. external table pin与 strict loader 是否还可被 self-sync、duplicate或非规范hex绕过；
3. lifecycle 中 column→standardize/clip→family norm 的 round与failure位置是否无歧义；
4. study-only cap和 `UNKNOWN` 成本/可达性是否被如实限定；
5. V2 是否确实没有恢复“当前最小组合”“G-ready”“formal-ready”主张。

在独立复核前，本轮只报告 **post-fix candidate study**，不报告 acceptance。
