# MODEL-INPUT-V2S 独立提案 A

> 日期：2026-08-01  
> 状态：`INDEPENDENT DESIGN PROPOSAL / NOT MACHINE CANON / NOT CLOSED`  
> 作用域：只重建从 `FeatureVectorV2S` 到 C01--C05 输入的 universe、矩阵和冻结边界；
> 不决定 routing，不修改 primitives，不声称 classifier、G 或正式 3200 已通过。

## 0. 独立性与输入边界

本提案只使用以下输入：

| 输入 | 本轮读取的 SHA-256 | 用途 |
|---|---|---|
| `QUESTION.md` | `8733d30e9f44d5765dfa02b54da1a1e9328cb7af155bff01d283d017ea683377` | 原问题、observation cut、claims 与不负责边界 |
| `EXECUTABLE-ATTACK-PROFILE.json` | `64a4e366a67ec2c12b1194d6fb01fab5b633529035a16f20b22acbf83346e5a7` | 3200 population、C01--C05 名称、资源上限与 replay 要求 |
| `FEATURE-V2-ROOT-DECISION.md` | `a811042a485ec9800957334690d19a7aa49d078259d3ee7e3f77b8dd2a768578` | V2S 已选择但未闭合的 model-input 要求 |
| `V2S-PRIMITIVES.candidate.json` | `2786e83d36a4d709915c84b57994b351dc29100a104413b6832c508fa197226b` | identity、rational、count、ngram 和 canonical 语义 |
| `FEATURE-VECTOR-V2S.candidate.schema.json` | `8fe1a3185adfcdd9579400d80a84b236ebbf493b037f9f8d957ec12d56f8e2a3` | predictor 的三类 rows 与排序约束 |

我没有把正在修改的 routing candidate、旧 feature engine、reference extractor 或旧 evaluator
当成答案，也没有读取它们来反推“现有实现想要什么”。因此下文是一个竞争设计，不是对旧实现的
说明书。

这里没有需要自研的新学习算法。最简单的可行内核是成熟的 sparse matrix、SHA-256、
binary64、exact-rational 预处理以及五个常见分类器。通爻需要明确的是这些成熟部件之间的
**身份、冻结、缺失、碰撞、排序与失败边界**。如果一个标准 sparse stack 能逐字节实现这些
边界，直接使用就是正向结果。

## 1. 先回答什么，不回答什么

本层的输入是已通过 receipt/routing/primitives 校验并带外部 pair binding 的
`FeatureVectorV2S`；输出是：

1. label-blind 的 row/universe/column/transform manifests；
2. C01 exact-presence view；
3. C02/C05 continuous view；
4. C03/C04 presence view；
5. canonical sparse binary64 matrix bytes 与 bindings；
6. calibration-only OOV、holdout drift 和失败 receipt。

本层不回答：

- routing 是否覆盖所有 receipt leaf；
- 某个 classifier 是否达到控制灵敏度或 T 等价阈值；
- logistic solver、tree tie break、KNN distance reduction 的最终机器语义；
- 最适合的 categorical hash 宽度；
- 4096 categorical buckets 是否优于 exact sparse one-hot；
- family normalization 是否在真实攻击分布上增加净功效；
- 正式运行是否满足 4 GiB / 3600 秒上限。

这些必须由后续机器包、差异实验、两份 clean-room 实现和实际 shape rehearsal 回答。

## 2. 核心判断：不能只选一种 universe

### 2.1 竞争方案 S：完全 static route-derived universe

在读取任何 calibration feature vector 前，由冻结 routing 枚举全部列。

优点：

- universe 与 calibration 样本偶然性无关；
- holdout 不会自然地产生“未知列”；
- label-blind 边界最清楚。

不能完整解决的地方：

- open string、record digest、typed number value 等 categorical `value_sha256` 的取值空间不可枚举；
- 若 ordered context 的 index 上限很大，完整展开会在读一行数据前就制造不可接受的稀疏维度；
- 把 open value 强行 hash 后，C01 就不再是 exact categorical scan。

所以纯 S 不能唯一实现 C01。

### 2.2 竞争方案 C：完全 calibration-derived universe

先读取 calibration predictor artifacts，在 label join 前把实际出现的全部 identity 排序冻结。

优点：实现最短、矩阵最小、天然适配 open categorical values。

致命问题：若 holdout 首次出现一个 numeric identity、missing identity 或新 ordered index，完全 C
只能静默丢列或在线扩列。前者可把只存在于 holdout 的泄漏变成假绿；后者改变冻结模型输入。
把它记一条 warning 也不够，因为 profile 要求 warning count 为零。

所以纯 C 不能作为正式默认方案。

### 2.3 建议方案 H：结构静态、开放值 calibration 冻结

H 不是折中话术，而是按“identity 是否由 schema/routing 有限决定”分层：

| identity | 冻结来源 | holdout 新值 |
|---|---|---|
| family 顺序与 channel/stat 合法矩阵 | static routing | 不可能；出现即 `NOT_QUALIFIED_SCHEMA_DRIFT` |
| 固定 numeric identity | static routing expansion | 未登记即 schema drift |
| bounded `ORDERED(index)` numeric identity | 优先 static expansion；超资源才允许 calibration 备选 | calibration 备选下首次出现即 schema drift，绝不丢弃 |
| 每个 numeric identity 的 missing 列 | 与 numeric identity 同时 static 冻结 | 未登记即 schema drift |
| categorical hash buckets | static | 无新列；所有合法值都有桶 |
| ngram family × 4096 direct buckets | static | 无新列 |
| family norm | static seven columns | 无新列 |
| 固定 atom 的 exact category（MISSING、closed branch、closed residue） | static routing + TVE2 | 未登记即 drift |
| open exact category row identity | calibration feature bytes，读取 label 前 | 合法 `C01_OOV`；C01 为 0，hashed view 仍接收 |
| numeric center/scale、tree threshold candidates | calibration values，读取 label 前 | 不扩列；只应用冻结参数 |

这里必须区分两种“holdout-only”：

- **开放值 novelty**：已知 family/context/channel 下出现新 `value_sha256`。这是 categorical world
  的正常变化，不是 schema drift。它不能进入已冻结 C01 exact dictionary，但必须进入 signed
  categorical bucket，并写入 `C01_OOV` audit。
- **结构 identity drift**：新 family/context/channel/stat、numeric identity、missing identity 或
  未登记 ordered index。这意味着 calibration/model contract 没覆盖 routing 可生成的结构，整个
  challenge 为 `NOT_QUALIFIED_SCHEMA_DRIFT`。

这一区分防止把动态世界误报成协议错误，也防止用“动态世界”当理由静默漏掉结构信号。

### 2.4 关于 ordered index 的仍存分歧

首选是让 routing 给出每条 ordered route 的闭区间并静态展开。若实际展开量使 model-input
超过资源 ceiling，应比较：

1. calibration 冻结 index，holdout-only index fail closed；
2. 删除 per-index model columns，只保留 primitives 已定义的 13 项 ordered-series summary；
3. 给该 route 一个独立、固定宽度且保留 route context 的 numeric hashing 设计。

第 3 项是新机制且存在 numeric collision，目前没有必要先引入。若第 2 项在构造性测试中没有
损失检测能力，它比第 1、3 项更简单。此分歧必须由 routing 的实际 expansion 大小和 index-only
leak counterexample 决定，不能在 prose 中假定。

## 3. 冻结时序：先 membership，再数据，再 label

每个 challenge（D0、D1、T）独立执行以下时序；static manifests 可以共享，但 calibration-derived
内容不能跨 challenge 借用：

1. 绑定 challenge、phase、block、公开 slot ID、predictor/audit exact pair、primitives、routing、
   vector schema 和 provider hashes；冻结 calibration membership。
2. 只把 calibration predictor bytes 交给 `universe builder`。该进程在 OS/进程权限上不能读取
   role map、label reveal 或控制 registry 的 role assignment。
3. 构造 static structural universe，枚举 open exact category identities，计算 numeric
   center/scale 和 tree threshold candidates。
4. 生成 canonical universe、column、row、transform manifests并外部锚定。
5. 关闭 universe builder 后才把 calibration labels按冻结 row manifest join给 C01--C05 trainer。
6. holdout feature extraction只允许应用已冻结 manifests；不得扩列、重估 scale、重选 threshold、
   重设 hash width或依据 holdout label修补 OOV。
7. holdout predictions冻结后，才按 profile 执行 label join、CI 与 within-block permutation。

“代码里先没用 label”不是 blindness 证据；第 2--4 步需要有真实不可读 label 的执行隔离和输入
receipt。否则 calibration-derived universe 可能被 role 选择污染。

## 4. 三个 classifier view

### 4.1 C01：`EXACT_CATEGORY_PRESENCE`

列由两部分组成：

1. static fixed-atom exact rows；
2. 本 challenge calibration 中出现过的 open categorical row identities。

完整列 identity 是 primitives 定义的原始 tuple：

```text
family_utf8 || raw_CTX2 || channel_identity || raw_value_sha256
```

排序使用 primitives 的 raw tuple ascending。单元格是 binary64 `1.0` 当且仅当该 receipt 中至少
一个 categorical row 命中该 exact identity；否则为 `0.0`。count 不在 C01 重复编码，因为 C01
要检验 exact category 的存在而不是次数阈值。C01 的 calibration dictionary 在 label join 前冻结；
label 只能选 rule，不能选列。

D0/D1 若要求 C01 成为 primary detector，private family 必须构造至少一个跨 calibration/holdout
复现的 exact atom，或一个由 static fixed-atom 表达的 branch/missing signal。若每个 slot 都使用
新的随机 token，C01 无法从 calibration exact identity 泛化到 holdout；这应判定为 control design
与 primary detector 不匹配，而不是让 evaluator 偷读 private registry 后临时加列。

### 4.2 C02/C05：`CONTINUOUS_HASHED`

逻辑列块按以下固定顺序拼接：

1. `NUMERIC_VALUE`：按 static numeric identity 顺序；
2. `NUMERIC_MISSING`：与第 1 块一一对应、同顺序；
3. `CATEGORY_SIGNED_BUCKET`：七个 family 固定顺序，每 family bucket 递增；
4. `NGRAM_DIRECT_LOG`：七个 family 固定顺序，每 family `0..4095`；
5. `FAMILY_NORM`：七个 family 固定顺序。

建议的第一候选 categorical bucket width 是每 family `4096`，理由只有一个：它复用 ngram 已有
固定宽度、在 3200 行下可用 mature CSR 执行；这不是功效结论。还必须和 `8192`、`16384` 以及
“直接复用 C01 calibration exact sparse columns”竞争。

对每个 categorical row，先重建完整 category row preimage，再计算：

```text
d = SHA256(
      FRAME32("WAVE025_MODEL_CATEGORY_HASH_V2S") ||
      FRAME32(category_row_preimage)
    )
bucket = U32_BE(d[0:4]) mod categorical_bucket_width
sign   = +1.0 if (d[4] & 1) == 0 else -1.0
magnitude = LOG1P_BITS[min(count_u64, 255)]
```

同一 row/family/bucket 的值按完整 category row identity 排序后逐步 binary64 相加。bucket 不跨
family。count 大于 255 明确饱和；`LOG1P_BITS[0..255]` 来自 deterministic-math artifact，禁止
运行时调用未登记 libm。

ngram 已经是 route-aware preimage 后的 family direct bucket。其连续值是
`LOG1P_BITS[min(count_u64,255)]`；不再二次 hash，不跨 family，不增加 context 列。

### 4.3 C03/C04：`PRESENCE_TREE`

逻辑列块和 continuous view 同序，但两类 sparse block改为：

```text
CATEGORY_BUCKET_PRESENT[f,b] = 1.0
  iff 存在至少一个 categorical row 命中 (f,b)

NGRAM_BUCKET_PRESENT[f,b] = 1.0
  iff 对应 ngram_count > 0
```

category presence 是 **OR**，不能由 signed bucket sum 是否非零推导。若 +x 与 -x 在同一 bucket
抵消为 `+0.0`，presence 仍是 `1.0`。ngram presence 同样不以 log count 的舍入值为真值来源。

numeric value、numeric missing和 family norm保持连续值。C03 的 threshold candidates 与 C04
每个节点可用的 threshold universe，都必须由 calibration matrix values在 label join 前冻结。
label 可以选择冻结候选，不能通过 label 新造阈值。具体 stump/tree loss、depth、min-leaf 与 tie
规则仍属于 classifier artifact，不在本 model-input 提案中伪装闭合。

## 5. Numeric + missing 的唯一建议语义

对每个 static numeric identity `j`，在本 challenge calibration 中只用 present exact rationals
计算：

```text
center_j = exact type-7 median
q1_j     = exact type-7 p=1/4
q3_j     = exact type-7 p=3/4
scale_j  = q3_j - q1_j, if nonzero
           1/1,          if zero or no spread
```

若 calibration 从未 present，`center_j=0/1, scale_j=1/1`，并记录 label-blind
`CALIBRATION_ALL_MISSING`，但列仍保留。

对每行：

```text
present: value   = round_binary64((x_j - center_j) / scale_j)
         missing = +0.0
absent:  value   = +0.0
         missing = 1.0
```

所有 rational 运算在转换前继续遵循 primitives bounds。conversion overflow、nonfinite、
subnormal/tie 未按 deterministic-math artifact处理时 fail closed。所有 `-0.0` 在写 matrix 前改成
bit pattern `0x0000000000000000`。

选择 `scale=1` 而不是“zero-IQR 就整列置零”，因为后者会漏掉 calibration 常量在 holdout 改变的
信号。缺失列必须为每个 numeric identity静态存在；仅用 value 的 0 imputation 会把“缺失”与
“恰好等于 center”坍缩。

这是建议，不是已证明最佳的统计标准化。mean/std、MAD 等成熟方案可作为竞争者，但同一正式
profile 只能冻结一个，不能在 control 结果出来后选择。

## 6. Family normalization

对 continuous view，先在每个 family 内按该 family 的 column order形成未归一化向量：numeric
value、numeric missing、signed categorical和direct ngram。使用 deterministic-math 指定的逐项
square、固定顺序 sum、sqrt得到 `norm_f`。

```text
norm_f > 0: 该 family 的四类 component 全部除以 norm_f
norm_f = 0: component 保持 +0.0
FAMILY_NORM[f] = norm_f
```

因此方向信号不会被一个超长 benign family仅凭 leaf 数淹没，同时 norm column保留该 family
总量本身可能携带的泄漏。presence-tree view不除以 norm：numeric standardized value和两类 OR
presence直接进入矩阵，但复用同一个 `FAMILY_NORM[f]` 连续列。

这里仍有真实分歧：family normalization可能把一个 family 内“出现一次”和“出现一千次”的
差异主要压到单一 norm 列，可能损失局部 count power。必须做 on/off ablation；若不归一化在相同
成本下对所有构造性 leak更强且 T 不恶化，应删除 normalization，而不是因 V2S 已写出它就保留。

## 7. Row、column 与 challenge 边界

### 7.1 Row order

每个 `(challenge, phase, view)` 生成独立矩阵。challenge 固定顺序为 D0、D1、T；phase 固定为
`CALIBRATION`、`FRESH_HOLDOUT`。矩阵内部 row key：

```text
(block_u32 numeric ascending, public_slot_id raw UTF-8 byte ascending)
```

`public_slot_id` 必须在 challenge/phase 内唯一。row manifest逐行绑定 slot ID、block、predictor
bytes length/SHA、audit bytes length/SHA和 exact outer-pair receipt SHA；不包含 label/role。

label artifact随后只能以 `(challenge, phase, public_slot_id)` exact join；missing、duplicate、extra
或 block mismatch均失败。不得依赖 filesystem order、JSON object order或 runner completion order。

### 7.2 Column order

七个 family 的唯一顺序就是 primitives 中的 exact enum顺序 F01--F07。

- numeric identity：`family_utf8, raw_CTX2, channel_ascii, stat_ascii` raw tuple；
- C01 exact category：完整 categorical raw tuple；
- categorical hashed/ngram：family 顺序后 bucket numeric ascending；
- family norm：family 顺序；
- view block：按第 4 节列出的 block 顺序，不做跨 block lexicographic merge。

每个 column manifest row含 `column_u32`、`view`、`block`和该块的完整 identity或 bucket。连续
column index必须从 0 开始无空洞；manifest bytes在任何矩阵构造前冻结。

## 8. Canonical sparse binary64 bytes

3200 × 57344（仅 4096 categorical + 4096 ngram，每 family）的 dense float64 已约
1.47 GB；continuous与presence各存一份，再加 solver和 replay工作区，会危险地接近或超过
4 GiB。使用 dense 矩阵不比成熟 CSR 更有研究价值。

本提案建议 canonical `MCSR2`，其逻辑值仍是 binary64 matrix：

```text
magic       = ASCII "MCSR2\0"
rows        = U64_LE
columns     = U64_LE
nnz         = U64_LE
row_ptr     = (rows+1) × U64_LE
column_idx  = nnz × U32_LE
values      = nnz × IEEE-754 binary64 little-endian bits
```

约束：

- 每行 `column_idx` 严格递增，禁止 duplicate；
- exact `+0.0` 不写入 CSR，所有计算所得 `-0.0` 先规范为 `+0.0` 再省略；
- NaN、±Inf、signaling NaN全部禁止；
- dimensions 或 column index超界即失败；
- CSR 的语义零唯一，不允许 explicit zero；
- values 的计算/碰撞累加顺序由 column manifest与完整 source identity顺序决定，而不是 sparse
  library 的内部 coalesce 顺序。

little-endian 是跨实现**显式序列化格式**，不是“使用 host native endian”。big-endian host也必须
写 little-endian。若后续决定用 big-endian，只能生成新候选版本，不能在 loader中自动猜测。

定义 `FRAME64(x)=U64_BE(len(x))||x`，每个 matrix binding hash为：

```text
SHA256(
  FRAME32("WAVE025_MODEL_MATRIX_BINDING_V2S") ||
  FRAME32(challenge_ascii) ||
  FRAME32(phase_ascii) ||
  FRAME32(view_ascii) ||
  FRAME32(raw_32_byte_row_manifest_sha256) ||
  FRAME32(raw_32_byte_column_manifest_sha256) ||
  U64_BE(rows) || U64_BE(columns) || U64_BE(nnz) ||
  FRAME64(exact_MCSR2_bytes)
)
```

同时单独记录 raw `SHA256(MCSR2_bytes)` 与 byte length。binding preimage不包含 labels、predictions
或模型结果；否则同一输入无法被不同 classifier共享和独立重建。

是否使用 SciPy、Rust `sprs` 或自持 serializer不是协议身份。库只有在读回上述 bytes完全相同、
不自行 coalesce/reorder/保留 explicit zero时才合格。

## 9. 每项机制的移除反例

| 机制 | 删除后具体漏检或假绿 |
|---|---|
| structural universe static freeze | calibration 的 argv只有 index 0--2，hidden-role leak只在holdout index 3；index 3被静默丢列，T 假绿 |
| open exact category calibration freeze | D0 predecessor atom跨phase重复，但不是 routing fixed atom；C01没有可扫描的 exact列，primary control错误失败 |
| calibration label隔离 | universe builder按role挑选相关 category，D0小样本上过拟合；holdout看似灵敏却是标签选择泄漏 |
| numeric missing列 | hidden role只改变某optional scalar是否存在，present值恰好等于median；0-imputation后两类完全相同 |
| zero-IQR fallback `scale=1` | calibration值全为7，holdout hidden role变为8；“zero-IQR整列置零”会删除唯一信号 |
| signed categorical block | C02/C05看不到只有枚举值变化、numeric/ngram不变的已登记泄漏，两个classifier失去该攻击面 |
| category presence OR | 两个相反sign的category撞同bucket并抵消为0；C03/C04把“两项都存在”误判为“桶为空” |
| route-aware direct ngram | cwd与argv包含相同gram但role关联方向相反；抹掉route后聚合抵消，局部字符串泄漏消失 |
| ngram full 4096 direct block |只保留top-k calibration buckets，leak bucket只在holdout出现并被静默丢弃 |
| family separation | F02与F07同bucket的相反关联相消，canary信号被benign argv流量掩盖 |
| family normalization + norm column配对 | 只归一化不保留norm会漏掉“总量”泄漏；只留原值不归一化可让F01巨大benign体量淹没F07局部距离信号 |
| fixed row order | 两个provider按completion order写行，prediction仍按slot order join，产生错误标签对应 |
| fixed column manifest | calibration和holdout按首次出现顺序建列，同一column编号表达不同identity，模型输出无意义但shape一致 |
| canonical collision accumulation | sparse库以不同coalesce顺序累加 `a+b+c`，binary64 bits/hash漂移，double replay无法判断是哪一语义 |
| `-0 → +0` | 数学等价的两个provider写出不同matrix hash，产生伪 replay failure |
| holdout structural drift fail-close |新numeric identity被当作普通OOV忽略，恰好只有该identity含role leak，T假绿 |
| C01 cross-phase repeat要求 | 每个control slot用全新随机exact token，C01无法泛化；把primary失败误判成collector不敏感 |

这些是构造性必要性反例，不是实际功效结果。每项都必须变成 golden/ablation，证明 off/on 差异；
若真实实现不能复现表中差异，该机制的保留理由就不存在。

## 10. 不应保留的显而易见或冗余机制

在有反例证明必要前，删除以下内容：

- RAG、embedding、LLM、PCA/SVD、自动交互特征、polynomial expansion；它们没有解决本层的冻结
  和身份问题，反而增加不确定语义；
- 给 C02/C05 同时输入完整 open exact one-hot和 signed hash的双份 categorical表达；先让两者
  竞争，不能为了“可能更强”全部堆叠；
- 同时保留 z-score、robust scale、rank transform 三份 numeric副本；
- 把 audit paths、receipt hashes、source filenames、slot IDs、block/phase或host truth复制进
  predictor matrix；这些会产生直接捷径；
- generic recursive count、bag item index、family-global lexical context；primitives/routing已明确
  它们为什么错误；
- C03/C04 从 signed sum推导 presence；已有可执行collision反例；
- 为 C01 构造 holdout-seen exact列；这是在线扩 universe；
- 用 holdout label选择 bucket width、family normalization、scale或threshold candidates；
- 同时输出 dense和CSR“方便调试”；第二份矩阵扩大hash面与内存，debug应从canonical CSR只读派生；
- 自研 SHA、sparse container或通用 logistic/tree/KNN内核；成熟实现满足 exact boundary就直接采用。

## 11. 关键竞争方案与区分实验

### E1：categorical 4096 vs 8192 vs 16384 vs calibration exact sparse

对相同 label-blind calibration、相同 synthetic/actual-shape receipts预先生成四套 universe，不读
role。比较：

- occupancy、collision、opposite-sign cancellation、每行 nnz；
- D0/D1构造性enum leak sensitivity；
- T role-null placebo与benign high-cardinality categories；
- C02/C05 wall time、peak RSS和artifact bytes。

若 exact sparse在资源内且功效不低，它比额外hash机制更简单，应采用；若 OOV/维度使其漏掉已
登记构造性攻击或越过ceiling，采用最小通过宽度。不得因为 4096 和 ngram 对称就选 4096。

### E2：ordered static expansion vs series-only

从最终 routing列出每个 ordered route的最大 index和静态列数。构造一个“只改变 index k、13项
series summary保持相同”的成对fixture：若这种成对序列存在且属于威胁模型，series-only漏检，
必须保留bounded per-index；否则删除大规模index expansion。

### E3：family normalization on/off

固定相同列和labels，构造：

1. F01 benign体量 ×100，但F07有弱role signal；
2. role signal只存在于某family总norm；
3. 两family相反方向信号。

比较 C02/C05 control sensitivity、T false positive、collision和成本。normalization只有在“局部
信号不被淹没”且 norm column保住总量信号时才保留。

### E4：robust center/IQR vs simpler no-centering

构造 constant calibration + holdout shift、极端outlier、all-missing、巨大exact rational和
subnormal边界。比较可检出性与 deterministic-math复杂度。若 no-centering + fixed scale在所有
任务上不差，应采用更简单方案；不能把统计习惯当必要性。

### E5：presence OR 独立矩阵是否必要

公开生成已知 signed collision pair与重复 ngram count。若从 continuous CSR及其 source rows能
在不读audit的情况下唯一重建 OR view，可以只发布一套 source sparse事件加两个派生hash；若不能，
必须保留独立 presence matrix。不能让 classifier读取 audit sidecar来补救。

## 12. Golden、holdback 与两 clean-room 实现

### 12.1 Public goldens

最小 public suite至少包含：

1. numeric present/missing、all-missing、zero-IQR、`-0`、overflow/subnormal/tie；
2. static fixed atom与 calibration open exact category；
3. holdout-only open category（C01 OOV但hashed view存在）；
4. holdout-only numeric identity（必须 schema drift）；
5. 两个category同bucket同sign、同bucket反sign，验证sum与OR分离；
6. 同gram在cwd/argv route context产生独立preimage后进入direct family bucket；
7. ngram/category count `0,1,255,256,u64_max` 的饱和与 table bits；
8. family zero norm、normal component、norm-only total量信号；
9. row completion order打乱但matrix bytes不变；
10. column首次出现顺序打乱但manifest/matrix bytes不变；
11. CSR duplicate、unsorted index、explicit ±0、NaN/Inf全部拒绝；
12. C01 exact token跨phase重复与每slot随机token的对照；
13. 4097+ UTF-8 split经primitives后只验证model不二次解释；
14. 三个challenge各自 calibration universe，禁止跨challenge open exact借用。

每个case包含 exact feature-vector bytes、membership bytes、expected universe/row/column manifests、
MCSR2 bytes、raw SHA、binding preimage hex、binding SHA和预期失败码。

### 12.2 Secret holdback

协调者在 provider 开始前生成并外部锚定，不给实现者 expected output：

- Unicode/context framing近碰撞；
- category signed collision与count accumulation顺序；
- dynamic ordered index边界；
- OOV category和structural drift的相邻对；
- rational刚好落在binary64 tie、subnormal、最大finite附近；
- CSR最后一行空、全部行空、最大column、row_ptr边界；
- family norm中大量小值与单个大值导致的accumulation差异。

### 12.3 两份 clean-room provider

- Provider A：Python标准库 parser/manifest + pinned NumPy/SciPy sparse执行；
- Provider B：不读取 A 源码的 Rust 或 Go 实现，手工写 canonical serializer/CSR，使用独立
  SHA-256 与binary64 bit conversion库。

两者可以读同一机器规范与 public goldens，不能读彼此源码/中间结果。验收要求 public与secret
holdback上的以下对象逐字节一致：

- label-blind universe、row、column、transform manifests；
- C01、continuous、presence MCSR2 bytes；
- raw/binding hashes；
- OOV/drift reports与所有negative failure codes；
- 由相同matrix生成的 classifier输入读取结果。

只比较最终 prediction不够：两个错误provider可能在同一列错位上给出相同预测。

### 12.4 实际 shape rehearsal

在 G 前，以 3200 个 actual-shape receipts和最大尺寸fixtures跑完整 model-input两次，记录：

- universe columns、rows、nnz、每family density与collision；
- 每个 artifact bytes、peak RSS、temporary cache、wall time；
- CSR读取/训练期间是否发生隐式dense expansion；
- 两次的 manifests/MCSR2/hash是否零差异；
- C01 OOV和structural drift count；
- warning/nonfinite必须均为0。

## 13. 资源、功效与维护依赖

### 13.1 资源

若 categorical width 为4096，category + ngram的固定列是 `7×8192=57344`，另加 numeric和7个
norm列。3200行 dense float64仅固定块就约1.47 GB；continuous与presence并存约2.94 GB，尚未计
solver、KNN和replay，不能安全地把“4 GiB以内”当作已证明。

MCSR2 基础大小约为：

```text
30-byte header + 8*(rows+1) + 4*nnz + 8*nnz
```

即约 `12*nnz` bytes加row pointers。真实 `nnz` 完全依赖 routing/receipts，当前是 Unknown。
任何库若在 fit、distance或hash前隐式 materialize dense矩阵，都应在 rehearsal中拒绝。KNN可按
holdout block计算distance，避免同时保存全pair矩阵；这属于成熟工程选择，不是新机制。

### 13.2 功效

正式 calibration 只有 D0 100、D1 100、T 400，远小于固定特征维度。L2、bounded tree与KNN
的高维功效不是由 deterministic bytes保证的。尤其：

- C01只对跨phase复现的 exact atom有功效；
- signed hash宽度过小会碰撞，过大又使 calibration极稀疏；
- KNN在高维稀疏空间可能出现distance concentration；
- family normalization可能提升局部信号，也可能把count信号压到一个norm列；
- C03/C04在小 calibration上需要严格 bound与独立 T placebo，不能靠训练准确率判断。

profile中 `five_attack_union_bound_pass_probability_lower_bound=0.911276` 是设计输入，不是这套
model layout的实测功效。必须分别报告 D0/D1 classwise CI、T、role-null placebo与各 mechanism
ablation，secondary classifier不能挽救 C01 primary control失败。

### 13.3 维护与外部依赖

可以使用成熟库，但 release manifest必须绑定：版本、wheel/crate/module hashes、binary provider、
endianness和禁用的隐式行为。主要风险：

- NumPy/SciPy升级改变 sparse coalesce、dtype promotion或reduction order；
- BLAS/Accelerate和FMA使 classifier数学跨环境变化；
- sparse库停止维护或格式升级；
-标准 `.npz`/pickle不是这里的 canonical evidence格式；
- exact-rational到binary64若委托给不同语言默认parser，边界bits可能不同。

低成本自持部分只应包括约百行的 canonical MCSR2 writer/reader、manifest validator和hash binder；
不应自研 sparse algebra或分类器。这样外部库停更时，证据bytes仍可迁移到另一成熟执行库。

## 14. 当前 Unknown 与下一步判别点

1. 最终 routing 的 static numeric/index universe有多大；因此纯 static expansion是否可行未知。
2. categorical 4096/8192/16384/exact sparse哪一个在控制功效与4 GiB内最优未知。
3. C01 private family是否保证至少一个跨phase exact atom未知；否则现有primary mapping本身不可行。
4. family normalization对 D0/D1/T净功效未知。
5. robust median/IQR是否比更简单的no-centering带来净收益未知。
6. actual-shape receipt的每行nnz、collision、OOV和peak RSS未知。
7. deterministic-math尚未冻结，matrix bit-level结果不能成为canon。
8. C02 solver、C03/C04候选/tie、C05 distance/tie尚未机器闭合。
9. 两份clean-room实现和secret holdback尚未运行。
10. 本提案未证明任何 scientific claim、prefix qualification、G 或 formal 3200结果。

下一步最高信息量动作不是立即写 `MODEL-INPUT-V2S.candidate.json`，而是：

1. 等最终 routing冻结后计算 static expansion与actual-shape density；
2. 用 E1--E5 的构造性fixtures同时跑四个竞争layout；
3. 选择**最简单且不漏掉已登记反例**的一套，再把选择、失败语义和参数写成machine candidate；
4. 冻结 deterministic math 与完整goldens；
5. 才让两份clean-room provider开始。

如果 exact sparse one-hot + mature library在这些任务上完整胜出，应删除 signed categorical hash；
如果 series summaries完整覆盖 ordered攻击，应删除 per-index columns。反过来，只有真实反例证明
这些简单方案留下缺口时，才保留更复杂机制。研究价值是把 blindness资格问题解决，而不是保住
V2S 的机制数量。
