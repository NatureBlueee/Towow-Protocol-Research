# MODEL-INPUT-V2S 提案 A 独立红队

> 日期：2026-08-01  
> 状态：`REJECT_AS_EXECUTABLE_CANDIDATE / RETAIN_DESIGN_COMPONENTS / FORMAL_USE_BLOCKED`  
> 审查对象：`MODEL-INPUT-V2S-INDEPENDENT-PROPOSAL-A.md`，审查时 SHA-256
> `c114b149668127aeeaad1ad9558df88ce754aa8803b5d0f40dee869268750da6`。

## 0. 独立性、范围与结论

本轮没有读取旧 feature engine、旧 reference extractor 或 Pro 方案作为答案，也没有等待另一份
model-input 方案。本轮先从提案 A 自己承诺的输入、输出、blindness、C01--C05 view 和字节边界
构造反例；随后只读取当前 primitives、routing 与 control registry，以区分“提案内部没有定义”
和“应由外层提供、但目前尚未闭合”的依赖。

审查时与判定直接相关的外部材料为：

| 材料 | SHA-256 | 本轮只用于 |
|---|---|---|
| `FEATURE-V2-ROOT-DECISION.md` | `a811042a485ec9800957334690d19a7aa49d078259d3ee7e3f77b8dd2a768578` | 核对 model-input 必须回答的范围 |
| `V2S-PRIMITIVES.candidate.json` | `2786e83d36a4d709915c84b57994b351dc29100a104413b6832c508fa197226b` | 核对 predictor identity 与 missing 输入 |
| `FEATURE-VECTOR-V2S.candidate.schema.json` | `8fe1a3185adfcdd9579400d80a84b236ebbf493b037f9f8d957ec12d56f8e2a3` | 核对 model provider 实际能看到的字段 |
| `FEATURE-ROUTING-V2S.candidate.json` | `3aa9e17fd8d2d73bdc3e1434de48eec3209a1c2da2cb354023eb3fdb89694246` | 核对 finite/open/ordered/missing 是否可由机器推导 |
| `PRIVATE-CONTROL-REGISTRY.preformal-candidate.json` | `51dd8ced71a4090435117f0d68c98c65ccfa29928a7e0f422a8e451fef86fa39` | 核对 D0/D1 token 的实际稳定粒度 |
| `PUBLIC-CONTROL-FAMILY-REGISTRATION.preformal-candidate.json` | `aafe698ef0a70097e74a81d41e8fbe64d7e9a581766719f2cb2360da1ba1a21a` | 核对 primary C01 注册 |

结论不是“hybrid universe 不可行”。相反，提案 A 正确识别了 static structural identity、
calibration-frozen open value、holdout OOV 与 structural drift 不能混为一谈，也正确保留了 signed
category sum 与 tree presence OR 的区别。但它现在仍是一份研究提案，不是两个 clean-room provider
能够独立重建的候选。最承重的**内部 blocker**是：

> 提案只定义了一个 C01 binary exact-category matrix，没有定义 C01 detector 本身，也没有定义
> numeric exact/value、numeric missing、category count/context-total、support、conjunction、absence、
> OOV all-zero 与 tie 的机器语义。因此当前 primary C01 的“通过/失败”没有唯一含义。

即使 routing、admission 和 deterministic math 明天全部由外层补齐，这个 blocker 仍然存在。

## 1. 逐项裁决

`ACCEPT` 只表示该项局部语义可以进入下一版；不表示整份提案通过。

| ID | 审查项 | 裁决 | 原因 |
|---|---|---|---|
| A01 | static structure + calibration open-value 的 hybrid 总方向 | `ACCEPT` | 正确区分正常 OOV 与结构漂移，且禁止 holdout 扩列 |
| A02 | static / calibration identity 的机器边界 | `REJECT` | “fixed/open/bounded/资源过大”没有 route-level 机器分类、上界和唯一 fallback |
| A03 | calibration membership / label blindness | `REJECT` | freeze 只证明不再改，未证明 membership、public ID、block 与 builder 输入不由 role 派生 |
| A04 | C01 exact-category column identity与 holdout OOV 置零 | `ACCEPT` | raw family/context/channel/value identity 与不扩列方向清楚 |
| A05 | C01 可执行 detector：support、mapping、conjunction、tie、OOV fallback | `REJECT` | 提案完全没有给出唯一算法 |
| A06 | C01 numeric exact/value、numeric missing、ngram/count eligibility | `REJECT` | C01 view只含 binary categorical presence，未回答根决策要求的 channel eligibility |
| A07 | 当前 D0/D1 随机 token 与 C01 机制兼容性 | `ACCEPT` | 当前是“每 role 一个随机值，跨 calibration/holdout 复用”，不是 per-slot fresh；机制上可被 exact C01 学到 |
| A08 | 正式 V2S D0/D1 control binding 与实际灵敏度 | `UNKNOWN` | 当前 registry 明示 preformal/not-bound，且 D1 复用了已 reveal 值；新 formal 尚未生成和运行 |
| A09 | signed category sum 与 tree OR presence 分离 | `ACCEPT` | 正确阻断 opposite-sign cancellation 被误当作 absence |
| A10 | categorical width、count transform、collision accumulation 的最终字节 | `UNKNOWN` | width 未选，math table 与从 +0 开始的逐步运算尚未冻结 |
| A11 | exact-rational median/IQR、zero-IQR=`1` 的候选方向 | `ACCEPT` | 能区分 calibration constant 后的 holdout shift；选择仍需 ablation |
| A12 | numeric missing 的适用性与 MISSING2 映射 | `REJECT` | “numeric row 不出现”被直接当 missing；没有处理 union 不适用、部分 bag missing 或 expected-channel→stats 展开 |
| A13 | family normalization | `UNKNOWN` | 设计有合理反例，但净功效、sqrt/accumulation bits 与资源都未验证 |
| A14 | ordered index universe | `REJECT` | 正式语义在 static expansion、calibration fail-close、series-only 三者间悬空 |
| A15 | row/column 的逻辑排序方向 | `ACCEPT` | challenge/phase 分矩阵、block+slot 排行、identity 排列方向足够清楚 |
| A16 | row/column/universe/transform manifest 的 canonical bytes | `REJECT` | 没有 schema、字段闭包、serialization 或相互 binding |
| A17 | MCSR2 文件格式与 binding | `REJECT` | 缺 row_ptr/长度闭包、u32 column ceiling、manifest/spec/profile/transform bindings |
| A18 | binary64/log1p/sqrt/robust scaling 的正式 bits | `UNKNOWN` | 提案诚实延后；在 deterministic-math artifact 前不能作为 canon |
| A19 | 4 GiB/2 GiB cache/200 MiB output/3600 s ceiling | `UNKNOWN` | 只有 dense 粗算，没有 actual-shape nnz、C01 dictionary 或 solver peak 实测 |
| A20 | 双 clean-room + secret holdback 方法 | `ACCEPT` | 比只看 prediction 强；但必须先关闭 A02/A05/A06/A12/A14/A16/A17 |

## 2. 内部 blocker 1：C01 只有矩阵，没有 detector

### 2.1 缺少的不是 classifier artifact 细节，而是 model-input 自身的语义

提案把 C01 定义为 `EXACT_CATEGORY_PRESENCE`，单元格只有 `0.0/1.0`。随后只说“label 可以选
rule”。这不足以唯一回答：

- 一个 rule 是单列 presence、单列 absence、`context -> value` mapping，还是多列 conjunction；
- 是否允许 category count、numeric exact equality、numeric single threshold、numeric missing、
  ngram presence；
- minimum total support 与 minimum per predicted class support；
- 一个 feature 同时出现在两类时怎样定向；
- 多个同分 rule 的排序；多个 rule 怎样合成一个 prediction；
- 没有 rule、holdout 全 OOV、matrix row 全零或两类 prior 相同时预测哪一类、是否 abstain；
- missing atom 是普通 exact category、absence rule，还是 numeric identity 的 missing branch；
- calibration 选择何时冻结、冻结哪些 rule bytes、holdout 何种差异算 reselection。

这些不能全部推给后续 logistic/tree/KNN artifact。C01 本身就是 primary detector；它的输入资格与
rule family 是本层必须冻结的接口。

### 2.2 最小反例 C01-COUNT：presence 删除了唯一信号

同一 `family/context/channel/value_sha256` 在两类都存在：

```text
role R: count_u64 = 1
role S: count_u64 = 2
```

calibration 与 holdout 都保持相同关系。FeatureVectorV2S 明确保留 `count_u64`，但提案的 C01
把两者都写成 `1.0`。若“exact categorical scan”允许 context-total 或 exact count mapping，提案
机械删除了正控；若不允许，必须明确说 C01 不负责 count。当前没有唯一答案。

### 2.3 最小反例 C01-NUMERIC：numeric exact 与 missing 没有进入 C01

```text
role R: numeric identity j = 7/1
role S: numeric identity j = 8/1
```

或：

```text
role R: optional numeric j present, value equals calibration center
role S: optional numeric j explicitly MISSING2
```

所有 categorical exact 与 ngram row 完全相同。提案的 C01 matrix 对两类逐字节相同。根决策要求
C01 明确 raw exact/numeric/missing/ngram 哪些可成为候选；“一个都不进入”可以是一个有界选择，
但必须被明确选择并证明不破坏 primary control，而不能由文档标题默默决定。

### 2.4 最小反例 C01-XOR：conjunction 未定义

四个 calibration row：

```text
R: {A,B}
R: {}
S: {A}
S: {B}
```

每个单列的 class presence 完全平衡；`A XOR B` 才区分类别。提案没有说明 C01 只准单列，还是
允许二阶 conjunction/absence。允许任意 conjunction 会产生组合爆炸与过拟合；禁止则必须把这种
攻击列为 C01 不负责，并确认 D0/D1 不依赖它。当前结果会随实现者自行补义而变化。

### 2.5 最小反例 C01-SUPPORT：没有 support 就能系统性过拟合

100 个 calibration row 各带一个只出现一次的 open token，且 holdout 全部换成 fresh token。若 C01
可从 labels 选择 singleton rule，calibration 上可以形成大量完美规则；holdout 全 OOV 后所有 row
归零。提案既没有 support 下限，也没有 no-rule/all-zero prediction。因此两个实现即使使用相同
matrix，也能给出不同 primary control 结果。

### 2.6 必须补成什么

下一版至少需要一个 closed `C01_RULE_FAMILY`：eligible source channels、candidate serialization、
support 计算、允许的 arity、class orientation、rule 排序、selection/tie、fallback、OOV 与冻结时序。
若选择最简单的单 exact-token presence，应直接写出“不读 count、不读 numeric/ngram、不做
conjunction”，再用当前 D0/D1 与针对性反例证明它足以承担 primary mapping。

## 3. 内部 blocker 2：hybrid universe 的分界没有机器化

### 3.1 `fixed` 与 `open` 不能从 FeatureVectorV2S 自身唯一推出

model provider 看到的是 family、CTX2、primitive channel/stat 和 value digest，不看到 route ID。
两个 path 都可能产生 `EXACT_CATEGORY`：一个来自 closed enum，另一个来自 unrestricted string。
除非 routing 派生的 model registry明确列出每个 concrete identity 的：

```text
universe_kind = STATIC_ENUM | STATIC_NUMERIC | STATIC_MISSING |
                CALIBRATION_OPEN_CATEGORY | BOUNDED_ORDERED | FORBIDDEN
```

并绑定 finite values / expected stats / index bounds，否则 provider 无法仅凭 digest 判断一个 holdout
新值应当是 `C01_OOV` 还是 `NOT_QUALIFIED_SCHEMA_DRIFT`。

### 3.2 最小反例 UNIVERSE-ADJACENT

```text
U1: known context C_open, new holdout value digest x
U2: known ordered parent C_ordered, new holdout ORDERED(3) numeric identity
```

提案希望 U1 记 OOV 并送入 hash，U2 fail closed。但它没有冻结 C_open 的 open 身份，也没有冻结
C_ordered 的合法 index interval。两个 clean-room provider 可以合理地分别把 U2 当合法 bounded
novelty或 structural drift。

### 3.3 ordered fallback 使分界继续依赖实现环境

当前 routing 有两个 unbounded-by-schema concrete-index series，primitives 又允许最多 1,000,000
container items。提案提出“优先 static，超资源才 calibration 备选”，但没有定义：

- 按哪个机器可计算公式判定超资源；
- 使用 4 GiB、2 GiB cache、200 MiB output 中哪个 ceiling；
- 在读 calibration 前还是 actual-shape rehearsal 后决定；
- 同一 profile 在不同 provider 内存环境下能否选择不同方案；
- 何种决定被 precommit，何种变化要求新 profile/version。

正式候选必须选定一种语义，不能把资源探测当运行时分支。

## 4. 内部 blocker 3：freeze 不等于 membership blindness

提案要求“冻结 calibration membership”，并让 universe builder 的 OS 权限不能读 role map。方向
正确，但缺少可验证的 membership provenance：

- membership 的 exact bytes/schema/hash；
- membership 是在 role assignment 前产生，还是由一个读过 role 的 controller 选择；
- public slot ID、block、phase 与 role seed/domain 的独立性；
- builder 实际可读目录是否只含 predictor pair 与 role-free membership；
- audit sidecar、private registry、host-only fields、reveal、日志和文件名是否均不可读；
- builder executable/source/env 与其 output manifest 的 receipt；
- universe algorithm 是否必须“全收录”，从而禁止用 public ID/block 作任意筛选。

最小不可区分反例：两个 hidden worlds 拥有相同 predictor bytes，但 controller 根据 role 生成不同
membership/public-ID manifest。builder 即使从未打开 `role-map.json`，其 output 仍可随 hidden role
改变。`freeze` 只能证明这个泄漏后来没改，不能证明它不是 leak。

这有两层结论：membership 独立性事实需要 runner/precommit 外部证据；但“model package 必须绑定
哪一个 membership receipt、禁止读取哪些输入”是提案 A 自己缺少的内部接口。

## 5. D0/D1：随机性不是问题，稳定粒度才是问题

提案正确警告 per-slot fresh exact token 与 primary C01 不匹配。当前 preformal control 实际不是
这种设计：

- D0 是两个独立 16-byte CSPRNG tag，**每个 role 一个值，跨 calibration/holdout 复用**；
- D1 同样要求每个 role 恰好一个 stable token，跨 calibration/holdout 复用；
- 两者都注册 `C01_EXACT_CATEGORICAL_SCAN` 为 primary，secondary 不能救 primary。

因此“token 是随机生成的”不会机械破坏 C01；只要随机值的复用单位是 role×family，而不是 slot，
calibration open dictionary 会含两个 role atom，holdout 可再次命中。这一局部机制判定为 `ACCEPT`。

但当前 private registry 的状态是
`PREFORMAL_CANDIDATE_NOT_BOUND_REUSES_REVEALED_D1`，不是 formal V2S 证据。正式 control manifest还应
机器绑定：

1. exactly two distinct values；
2. one value per role；
3. same value across both phases；
4. expected family/context/channel；
5. C01 rule family确实能选到这个 atom；
6. private registry只作 reveal/audit，不给 universe builder 或 predictor；
7. 新 formal D0/D1 值均 fresh，T 中零 ingress。

若未来改为 per-slot fresh，正确结论是“control design 与 primary detector 不匹配”，不是让 evaluator
读 private registry后创建 holdout columns。

## 6. signed hash 与 presence OR：方向正确，字节仍未闭合

提案正确规定 categorical bucket 不跨 family，并把 `CATEGORY_BUCKET_PRESENT` 定义成 source rows
命中 bucket 的 OR，而不是 `signed_sum != 0`。以下反例被正确处理：

```text
category A -> bucket b, sign +, count 1
category B -> bucket b, sign -, count 1
continuous[b] = log1p(1) + (-log1p(1)) = +0
presence[b]   = 1
```

这是可以保留的局部成果。但 machine release仍需补：

- category width 的唯一值；
- accumulator 从 canonical `+0.0` 开始、每步 round、每步还是末步规范 `-0`；
- `LOG1P_BITS[0..255]` 的 exact 2048 bytes/hash/index endian；
- overflow/nonfinite 与 checked source count；
- OR 是直接由 predictor categorical row set产生，不能从 audit sidecar或 continuous CSR反推；
- presence matrix 与 continuous matrix分别绑定同一 source-vector population。

`E5` 询问能否从 continuous CSR“及其 source rows”重建 OR。若 source rows就是未经 hash 的 predictor
categorical rows，这相当于保留第三个 canonical input；若只剩 continuous CSR，则 opposite-sign
cancellation 已证明不可逆。下一版应明确哪个 artifact 是权威 source，而不是以“可派生”模糊掉它。

## 7. numeric 与 missing：robust scale 可保留，missing 语义必须重写

### 7.1 可保留部分

exact-rational type-7 median/IQR、只在最终进入 matrix 时 round，以及 zero-IQR fallback `scale=1`
都有清楚动机。反例成立：calibration 全为 7、holdout 变 8 时，zero-IQR 整列删除会漏检，
`scale=1` 不会。

### 7.2 “numeric row 不存在”不等于 missing

提案当前规则是：static numeric identity在一行 absent，就写 `missing=1`。至少三种现实会被混淆：

1. union/branch 下该 numeric identity根本不适用；
2. 适用但 optional leaf 缺失，routing 产生 `MISSING2(expected_channel)`；
3. BAG 中一部分 item present、一部分 item missing，numeric aggregate仍存在。

最小反例：

```text
row A: process_view = ERROR，ppid route不适用
row B: process_view = SUCCESS，但status.ppid缺失并有MISSING2
```

两行都没有 ppid numeric row。仅按 absence 会给两行同一个 missing bit；只有 B 才是该 numeric
identity 的真正 missing。虽然 branch category还能区分两行，这不使 numeric missing 的语义变正确。

### 7.3 expected channel 到多个 numeric stats 的映射缺失

一个 MISSING2 可以声明某 expected transform，而该 transform可能展开成多个 stats：string shape
有多项、integer residue有多项、ordered series有 13 项。提案说“每个 numeric identity有一个
missing列”，却没有说明一个 categorical MISSING row怎样、何时展开到这些列；也没说明 BAG 中
missing count是 OR、比例、count，还是只留在 categorical hash。

下一版应从 routing-derived applicability matrix生成每行状态：

```text
NOT_APPLICABLE | PRESENT | EXPLICIT_MISSING
```

并为每个 numeric identity冻结 missing bit的真值表。partial BAG missing应保留其 MISSING categorical
count；是否另造 numeric missing fraction需要单独反例，不能偷偷塞进 bit。

## 8. family norm 与 ordered index

### 8.1 Family norm：保持 `UNKNOWN`

把 family component 先做 L2 normalize、再保留原始 norm列，确实能同时表达方向和总量；但它不是
无条件保真变换。它会把同 family 内的局部 count幅度压缩到方向，并把大部分总量信息集中到一个
norm。提案已正确要求 on/off ablation，因此当前不应删除，也不应晋升。

机器层还缺：square/sum/sqrt 的逐步 bits、overflow/subnormal、division rounding、norm column是否
参与后续 standardization，以及 presence view所复用的 norm究竟由 continuous raw components还是
presence components产生。提案文字倾向前者，但 manifest必须逐字冻结。

### 8.2 Ordered index：当前为内部 `REJECT`

提案同时保留三种互斥语义：static per-index、calibration index + holdout fail、series-only。它还没
回答正式 provider应该实现哪个，因此不是普通 empirical unknown，而是接口未决定。

最有区分力的 pair不是任意“index k 改值”，而是两条 ordered series拥有完全相同 13 项 summary，
只有位置排列不同。若可构造并属于 threat model，series-only 会机械漏检；若不可构造或该攻击不在
作用域，per-index扩展可能是无价值成本。无论实验结果如何，选择必须在 formal data 前进入唯一
machine profile。

## 9. MCSR2 与 manifest：文件看似明确，仍可产生多个合法实现

### 9.1 MCSR2 缺少的结构不变量

header 与 little-endian方向清楚，但至少缺少：

- exact file length公式及 trailing bytes拒绝；
- `row_ptr[0] == 0`；
- `row_ptr` 单调非降且每项 `<= nnz`；
- `row_ptr[rows] == nnz`；
- `column_idx` 数量与 values 数量恰为 `nnz`；
- `columns <= 2^32`，因为 manifest叫 `column_u32`、index也是 U32；
- rows/columns/nnz乘加溢出的 parser规则；
- empty row、all-empty matrix与 zero-column matrix是否合法；
- signaling/quiet NaN应在读 raw bits后统一拒绝，而不是依赖 host float parser。

最小 malformed bytes：`rows=2, nnz=1, row_ptr=[0,1,0]`。字段长度全部对，但最后一个 pointer倒退。
当前 prose没有一条完整 validator rule明确拒绝它。

### 9.2 hash没有闭合语义来源

matrix binding包含 challenge/phase/view、row/column manifest SHA与 MCSR2 bytes，这是好方向；但它
没有直接或通过已定义 manifest schema绑定：

- exact model-input spec/version；
- primitives、routing、feature-vector schema；
- calibration membership；
- universe与transform manifest；
- category width、math table与provider；
- source predictor/pair population；
- selected attack profile。

更关键的是 row/column/universe/transform manifest本身没有 closed schema、canonical serialization
和 cross-binding。两个 provider可以构造逻辑相同但字节不同的 manifest，或者在同一 matrix上绑定
不同 preprocessing语义；当前 hash只会忠实记录分歧，不能告诉审查者哪一份符合规范。

### 9.3 逻辑 row/column order 可保留

每个 challenge×phase×view独立矩阵、row按 block numeric再按 public slot raw UTF-8、columns按
固定 block和 raw identity排列，是足够好的逻辑方向。下一步应把这些规则变成 closed manifest
schema与 public golden，而不是改换排序原则。

## 10. deterministic math、资源与 clean-room

### 10.1 Deterministic math 是真实外部依赖，不是已经完成的语义

提案诚实列出了 `round_binary64`、subnormal/tie/overflow、`LOG1P_BITS`、L2 square/sum/sqrt与固定
accumulation order。当前没有对应 machine artifact，所以本项为 `UNKNOWN`，不能因算法名称成熟就
宣称两个实现会有相同 bits。

public goldens还应覆盖：

- rational在最大 finite、最小 normal、最小 subnormal、half-ULP tie两侧；
- `a+b+c` 的非结合顺序与 signed cancellation；
- norm中大量小数后加一个大数；
- `count=255/256/u64_max` 饱和；
- scale rational在约分后刚好越过 digit ceiling；
- `center=0, scale=1, x=-0` 的 +0规范。

### 10.2 资源 ceiling 目前只有估算

提案正确指出 57,344 个固定 hash/ngram columns 的 dense 双矩阵危险，也正确倾向成熟 CSR。但正式
ceiling还包括 4 GiB RSS、2 GiB temporary cache、200 MiB output和 3600 s 总时限；当前没有：

- C01 calibration exact dictionary上界；
- ordered static expansion上界；
- actual-shape每行 numeric/category/ngram nnz；
- continuous、presence、C01 是否同时驻留；
- C05 sparse distance与 classifier fit 是否隐式 dense；
- matrix、manifest、OOV、model与统计总 output bytes；
- 两次 replay的峰值是否串行而不是重叠。

因此“使用 CSR”不是 ceiling 通过证据。若 rehearsal越界，结果应是
`NOT_QUALIFIED_NO_AUTOMATIC_PROFILE_REDUCTION`；不能在看过 formal data后改 width或 ordered策略。

### 10.3 Clean-room 方法可保留，但当前还不能启动实现验收

比较 universe/manifest/MCSR2/failure code 的 exact bytes，明显强于只比较最终 prediction；跨语言
实现与 secret holdback也有价值。验收包仍应再加：

- 两个 provider 的独立 source manifest、build dependency hashes与只读输入列表；
- 不共享 parser/serializer/oracle源码；
- 一个独立 strict reader/validator攻击 malformed MCSR2和 manifest；
- holdback input在实现开始前外部锚定，expected output不能由任一被测 provider单独定义；
- public golden、secret holdback、negative mutation三者都必须 byte/failure-code一致；
- 同一 provider双 replay与两 provider交叉一致分别报告，不能互相替代。

在 A02/A05/A06/A12/A14/A16/A17 修复前启动 clean-room，只会让两个实现者各自补义，比较的是
猜测而不是同一规范。

## 11. 内部 blocker 与外部依赖分账

### 11.1 即使所有外部依赖都已完成，仍必须修的 proposal 内部 blocker

1. C01 detector/rule family、numeric/missing/count/conjunction/support/OOV/tie 不存在；
2. static/open/bounded identity 没有 machine classification与唯一 ordered选择；
3. model package没有 membership receipt/input-read boundary；
4. numeric absence、not-applicable、MISSING2、partial BAG missing没有真值表；
5. row/column/universe/transform manifests没有 closed bytes；
6. MCSR2 validator与 binding closure不完整；
7. categorical accumulator seed/rounding与 source-of-OR artifact没有唯一化。

### 11.2 不能要求提案 A 单独证明，但必须作为外部 gate绑定的事项

1. collector V1.1 semantic admission是否通过；
2. routing structural/semantic coverage与 final SHA；
3. D0/D1 新 formal private registry、T zero ingress与实际 control sensitivity；
4. deterministic-math machine artifact；
5. C02--C05 classifier solver/tie/convergence；
6. 3200 actual-shape资源 rehearsal；
7. 两个 feature provider 与两个 model provider的独立一致；
8. G、D0/D1 classwise CI、T、role-null placebo和机制 ablation。

外部 gate尚未完成不能替提案内部 blocker背锅；反过来，修好 prose/schema也不能冒充这些实证。

## 12. 最有区分力的下一实验

下一步不应先写大而全的 `MODEL-INPUT-V2S.candidate.json`。最高信息量实验是一个预先冻结的
`C01-CONTROL-COMPATIBILITY-MINISUITE`，同时区分四种竞争 C01 定义：

1. single exact-token presence；
2. exact context→value/count mapping；
3. numeric exact/threshold + explicit missing；
4. bounded two-way conjunction。

最小 suite包括六组 calibration/holdout pair：

| case | 唯一变化 | 要区分的决定 |
|---|---|---|
| P1 | 当前 D0：每 role稳定 basename跨phase复现 | 最简单 C01能否承担 D0 primary |
| P2 | 当前 D1：每 role稳定 token跨phase复现 | 最简单 C01能否承担 D1 primary |
| P3 | 每 slot fresh token | 确认 exact C01应失败而不是偷读 registry |
| P4 | 同 category、count 1 vs 2 | C01是否负责 context-total/count |
| P5 | numeric 7 vs 8、present vs MISSING2 | C01是否负责 numeric/missing |
| P6 | XOR categories | 是否需要 conjunction，及其 support/成本代价 |

对四个候选在完全相同、label-blind universe上预先冻结：rule bytes、support、tie、all-zero fallback；
再比较 fresh holdout sensitivity、T role-null、rule count、artifact bytes与 wall time。选择**能通过 P1/P2、
不把 P3误判为可泛化，并且不为没有登记的 P4--P6复杂度付费**的最简单规则族。若 P4/P5是 root
要求的攻击面，就保留对应机制；若不是，明确列入 C01 不负责，由其他预注册 detector承担，但
secondary仍不能救 D0/D1 primary。

该 minisuite一旦选定 C01，才继续：冻结 universe-kind registry、numeric missing真值表、manifest
schemas、MCSR2 validator与 deterministic math；随后再让两个 clean-room provider开始。

## 13. 最终状态

提案 A 提供了可保留的研究构件：hybrid universe方向、OOV/drift区分、跨phase exact control条件、
signed-sum/OR分离、zero-IQR反例、固定 logical ordering、CSR方向和双 clean-room验收思路。

但当前不能把它直接翻译成 machine canon，也不能让 provider自行决定空白。决定为：

```text
PROPOSAL_A_DESIGN_COMPONENTS_RETAINED
PROPOSAL_A_EXECUTABLE_MODEL_INPUT_REJECTED
C01_PRIMARY_SEMANTICS_BLOCKING
FORMAL_G_NOT_AUTHORIZED
```

