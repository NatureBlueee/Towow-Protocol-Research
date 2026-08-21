# ChatGPT Pro independent return — Wave 025 model input

Task ID: `W025-MODEL-INPUT-PRO-B`  
Conversation: `https://chatgpt.com/c/6a6dce70-07f8-83ea-834c-0227e0a30e65`  
Capture: in-app browser visible assistant message after generation completed  
Evidence status: external independent candidate; not local evidence, not adopted, not formal

W025-MODEL-INPUT-PRO-B
总判定

最强方案不是纯 A，也不是纯 B，而是一个受限混合方案 H：

静态 route/schema 决定“什么身份是合法的、各身份如何排序、固定哈希块和 ngram namespace 如何解释”；T-calibration predictor 在标签不可读时，只负责激活 numeric identity、拟合稳健尺度、冻结 C01 候选。

形式上：

S
N
	​

=schema 允许的 numeric identities
C
N
	​

=T-calibration 中实际出现的 numeric identities

混合方案取：

U
N
	​

=C
N
	​

,并要求 C
N
	​

⊆S
N
	​


fresh holdout 中只要出现：

n∈
/
U
N
	​


就必须以 F010_HOLDOUT_NUMERIC_DRIFT 失败，即使这个 identity 在静态 schema 中本来合法。这严格满足题目给定的 holdout-only numeric 边界。

因此：

纯静态 A 只有在 route/schema 已经完整、有限、可验证，而且 schema 还给出了 calibration 未见 numeric 的外部尺度与缺失语义时才更好。按当前边界，静态展开 S_N \ C_N 只会制造全 missing 列；holdout 真出现时仍须失败，收益很小，成本却真实存在。

纯 calibration-derived B 适合一次性、封闭批次的机械复现测试，但不能证明语义可移植性：collector 把 argv 顺序搞反、把错误 stat 接到错误 route 上时，B 只会把它当成一个新合法 identity。

H 是当前条件下的竞争性首选。

在 route→identity binding 尚未完成时，任何方案最多只能获得“编译器字节一致”，不能获得 route-aware 模型输入资格通过。

另外有一个必须说清楚的下界：

一个 16384-bucket signed hash 本身不可能保证不存在抵消假阴性。

Signed feature hashing 是成熟的降维方法，交替符号的作用是让碰撞误差在期望上不单向累积、近似保持内积；它并不消灭碰撞，而且较小特征空间会提高碰撞概率。
scikit-learn
+1

所以，当前 C02/C05 若坚持单一 signed hash，只能依靠：

C01 的 exact token 视图；

C03/C04 的 unsigned OR occupancy；

或额外的 exact-dictionary shadow；

来阻止“hash 负结果被误读为无泄漏”。不能宣称 C02/C05 单独是 collision-free detector。

1. Problem reconstruction

这不是一个普通的“把字典转成稀疏矩阵”问题，而是四份合同必须同时成立。

1.1 语义合同

同一个 predictor 必须在两个 provider 中映射到同一个身份；不同身份不能因为文本拼接、排序、route 折叠或 argv 角色交换而合并。

需要区分：

numeric identity；

categorical context identity；

exact categorical token identity；

ngram namespace/bucket identity；

missing atom；

family；

route 所提供的是语义 namespace，还是仅为行政元数据。

特别是：

channel 和 expected_channel 必须同时进入 categorical identity；

typed CTX2 必须保留顺序和类型；

不能把 ordered argv 当成无序集合；

不能只 hash typed value SHA256 而丢掉其所在 context。

1.2 列宇宙合同

必须明确区分：

allowed universe：schema 允许什么；

active universe：本次 calibration 实际拟合什么；

fixed compressed universe：categorical hash 和 direct ngram；

candidate universe：C01 在 calibration 上冻结的 exact candidate。

holdout 只能被 transform，不能：

增加 numeric 列；

改变列顺序；

改变 TOP256；

改变 quantile、median、IQR；

改变哈希 key、bucket 数或 route namespace；

重新选择 C01 规则。

1.3 数值合同

“都用 float64”并不等于“字节唯一”。还必须冻结：

rational 如何约分和校验；

exact rational 如何舍入到 binary64；

分位数使用哪种定义；

IQR 为零时如何处理；

bucket 碰撞后以什么顺序求和；

family norm 如何累加；

sqrt、log1p 如何舍入；

-0.0 是否允许；

NaN、Inf、subnormal 的处理；

endianness。

NumPy 本身提供多种不同 quantile 方法；不显式冻结方法，即使输入相同，也可能得到不同的 median/IQR。
NumPy

1.4 字节与审计合同

SHA-256 只能绑定已经唯一的 bytes，不能替代 canonicalization，也不能隐藏低熵 label/case identity。SHA-256 是成熟、标准化的摘要算法，适合做完整性绑定；若要防止参与方预先搜索 bucket/sign，则可使用在 predictor 冻结前承诺、冻结后揭示的 HMAC-SHA-256 key。
NIST计算机安全资源中心
+1

模型 artifact 的 preimage 中不得进入：

label；

evaluator-private case ID；

audit sidecar；

path；

mtime；

source/provenance；

receipt path；

debug 信息；

provider build metadata。

这些可以存在于外部 receipt，但不能参与 classifier matrix。

2. Best design and strongest alternatives
2.1 三阶段架构
阶段 P0：公开语义冻结

在任何 provider 可读 label 前，冻结：

SPEC_VERSION

family 固定枚举及 rank

route/schema manifest

T-calibration membership manifest

fresh holdout membership manifest

opaque row ordinal

categorical hash 规则、bucket 数和可选 hash-key commitment

ngram namespace 规则

binary artifact 格式

failure-code precedence

D0、D1 不得参与 T 的：

numeric activation；

TOP256；

quantile；

median；

IQR；

collision dimension。

否则它们事实上变成额外的训练数据。D0/D1 可以在 H 冻结后用相同输入合同编译成诊断 artifact。

阶段 P1：pre-label calibration fit

provider 只能读取 T-calibration predictor，生成并提交：

active numeric identity manifest；

categorical contexts eligible for C01；

Q25/Q50/Q75 与 scale；

TOP256 token list；

column manifests；

count-transform table hash；

preprocessing manifest hash。

提交后才允许打开 calibration label。

阶段 P2：固定 transform

使用 P1 artifact 编译：

T-calibration；

2400-row fresh holdout；

必要的 D0/D1 diagnostics。

holdout 不允许改变 P1 的任何一个字节。

2.2 Canonical identity

定义：

LP32(x) = uint32_be(len(x)) || x

所有类型字段都使用上游已经冻结的 canonical bytes。不要在 provider 内自行做 Unicode normalization；若字段原本是文本，schema 必须直接规定唯一 UTF-8 bytes。

family rank 固定为：

0 F01_PUBLIC_INPUT_BYTES
1 F02_ARGV_ENV_CWD
2 F03_HOSTNAME_IDENTITY
3 F04_DIRECTORY_AND_SHARED_STATE
4 F05_PROCESS_NAMESPACE_FD
5 F06_TIMING_AND_ERRORS
6 F07_VISIBLE_CANARY
Numeric identity
NUM_ID =
  0x4E || 0x01 ||
  uint8(family_rank) ||
  LP32(typed_CTX2_bytes) ||
  LP32(channel_bytes) ||
  LP32(stat_bytes)

数值本身不进入 column identity。

每个 sample 对同一 NUM_ID：

0 行：missing；

1 行：observed；

大于 1 行：F007_DUPLICATE_NUMERIC。

即使两行 exact rational 完全相同也不合并；numeric 重复通常意味着 collector/admission 问题，静默求和没有清晰语义。

Categorical context 与 token
CAT_CONTEXT_ID =
  0x58 || 0x01 ||
  uint8(family_rank) ||
  LP32(typed_CTX2_bytes) ||
  LP32(channel_bytes) ||
  LP32(expected_channel_bytes)
CAT_TOKEN_ID =
  0x43 || 0x01 ||
  LP32(CAT_CONTEXT_ID) ||
  raw_32_byte_typed_value_sha256

不能只使用 value SHA256。否则同一个值位于 argv[0] 与 argv[1] 时会合并。

相同 exact token 的多行 count：

先用任意精度整数求和；

再做 min(sum,255)；

最后 transform 一次。

Ngram identity

理想形式为：

NGRAM_ID =
  0x47 || 0x01 ||
  uint8(family_rank) ||
  LP32(ngram_namespace_id) ||
  uint16_be(bucket)

其中 bucket ∈ [0,4095]。

这里存在当前 packet 的一个真实缺口：列要求是 route-aware，但冻结的 ngram row 只有：

(family, bucket, count)

因此必须满足二者之一：

route→namespace 已经被 typed predictor envelope 唯一绑定，并且 provider 能得到该 canonical namespace；

所有相关 route 对 4096 buckets 的语义完全相同，schema 明确证明它们共享一个 namespace。

否则必须返回：

F004_ROUTE_BINDING_UNRESOLVED

不能从 path、receipt 或 audit sidecar 猜 route。

2.3 Categorical signed hash

因为后续需要 family 内独立归一化，16384 buckets 应解释为每个 family 各 16384 个，而不是七个 family 共用 16384 个。

推荐普通确定性模式：

digest =
  SHA256(
    "W025-MI/CAT-HASH/v1\0" ||
    LP32(CAT_TOKEN_ID)
  )

bucket = uint16_be(digest[0:2]) >> 2
sign   = +1 if (digest[2] & 1) == 0 else -1

这样 bucket 使用 14 bit，sign 使用不重叠的 bit。

若 treatment 能根据公开 hash 规则自适应选择 token，使用：

HMAC-SHA256(K_hash, domain || LP32(CAT_TOKEN_ID))

其中：

K_hash 在 predictor collection 前随机生成；

先公开 commitment；

所有 predictor bytes 冻结后揭示；

key 与 labels、case IDs 完全独立。

如果不存在自适应攻击面，这个 keyed 层属于可删除复杂度，固定 SHA-256 即可。

2.4 Hybrid column universe
Numeric
S_N = schema allowed numeric identities
C_N = numeric identities observed in T-calibration

要求：

C_N ⊆ S_N
U_N = C_N

U_N 按 NUM_ID canonical bytes 升序排列，而不是：

calibration 首次出现顺序；

文件顺序；

dict insertion order；

path；

provider 自己的 locale。

fresh holdout 中出现任何 NUM_ID ∉ U_N：

F010_HOLDOUT_NUMERIC_DRIFT

不得静默忽略，也不得扩列。

Categorical

C02–C05 不建立 exact token vocabulary：

每 family 固定 16384 hash columns；

holdout-only categorical token 允许进入既有 bucket；

不扩列。

C01 的 exact token 与 context candidates 仅由 calibration predictors 冻结；holdout-only value：

exact presence rule：不匹配；

context mapping：进入 OTHER；

不产生新 rule。

Ngram

每个 (family, ngram_namespace) 固定 4096 direct columns，bucket 从 0 到 4095。

如果每 family 只有一个 namespace，则固定 ngram 列总数为：

7×4096=28672

若某 family 有 R
f
	​

 个真正不同的 namespace，则该 family 是：

4096R
f
	​


不能把语义不同的 route 强行压成同一个 direct bucket。

2.5 逐分类器输入合同
模型	Numeric	Categorical	Ngram	Missing / presence	Family norm
C01	exact rational equality atoms	exact token presence；single-valued context total mapping	推荐仅作为 TOP256 conjunction token	categorical context 有 MISSING/OTHER；numeric 有 exact MISSING	无
C02	robust-scaled，unclipped	signed hashed transformed counts	direct transformed counts	numeric 独立 missing indicator	family L2 normalize；追加 log1p(pre-normalization norm)
C03	raw binary64；missing 时 median fill	unsigned bucket occupancy	direct bucket occupancy	numeric missing indicator；presence 为 OR	无
C04	同 C03	同 C03	同 C03	同 C03	无
C05	robust-scaled 后 exact clip 到 [-8,8]	signed hashed transformed counts	direct transformed counts	numeric missing indicator	family L2 normalize；建议追加 raw pre-normalization norm

所有七个 family 都是 eligible。F07 不能被 compiler 特判删除；它是否只出现在 positive-control route 中，应由实验 routing 决定。

Numeric missing

对每个 active numeric identity：

C01：

observed：canonical rational atom；

absent：MISSING atom。

C02/C05：

observed：scaled value，missing=0；

absent：value=+0.0，missing=1。

C03/C04：

observed：raw rounded binary64，missing=0；

absent：calibration median rounded binary64，missing=1。

因此：

observed exact 0 != missing

不能只看 value column。

Categorical presence

对 C03/C04：

presence[f,b] =
  OR over all exact tokens in the sample
     whose hash bucket is b

它不是：

signed_sum[f,b] != 0

若两个 token 落入同 bucket 且 sign 相反：

C02/C05 signed value 可能精确为 0；

C03/C04 presence 必须为 1；

C01 exact token 仍分别存在。

Count transform

冻结一张 256-entry table：

L[k]=RN
64
	​

(log(1+k)),k=0,…,255

每项直接发布为 8-byte binary64，provider 不在运行时调用系统 log1p。

类别 token：

aggregate identical CAT_TOKEN_ID counts
cap at 255
lookup L[count]
apply sign
sum colliding exact tokens

ngram：

aggregate identical family/namespace/bucket counts
cap at 255
lookup L[count]

“先 transform 后聚合”必须禁止。

2.6 Robust scaling 与数值唯一性

成熟 RobustScaler 的基本语义是：在训练数据上拟合 median 和 IQR，之后对新数据只 transform。
scikit-learn

为了跨语言唯一，建议冻结：

quantile method = averaged_inverted_cdf

并在 exact rational 上计算。

对排序后的 exact rationals y[0..n-1]，按该方法对 q ∈ {1/4,1/2,3/4} 求值；中间加权仍保持 exact rational，最后才舍入。

定义：

median = Q50
scale  = Q75 - Q25
if scale == 0 exactly:
    scale = 1

不使用“接近零”启发式阈值。

C02：

x
′
=RN
64
	​

(
scale
x−Q50
	​

)

C05 先在 exact rational 域裁剪：

x
′′
=min(8,max(−8,(x−Q50)/scale))

再做一次 RN64。

rational canonical form

每个输入 rational 必须已经满足：

denominator > 0；

gcd(|numerator|, denominator)=1；

numerator=0 时 denominator=1。

否则失败：

F006_NONCANONICAL_RATIONAL
rational→binary64

定义为：

nearest IEEE-754 binary64
round-to-nearest, ties-to-even

并冻结：

overflow 到 ±Inf：失败；

NaN：失败；

subnormal：允许；

任何结果为 zero 时序列化成 +0.0；

不允许 -0.0 进入 artifact；

不通过 decimal string 中转。

IEEE 754 的 binary64 包含正负零、subnormal、Inf 与 NaN，基础加减乘除和平方根具有规定的舍入语义。
Oracle 文档
+1

bucket sum 与 family norm

禁止依赖稀疏插入顺序或 BLAS reduction 顺序。

推荐定义：

每个 binary64 被视为其精确 dyadic rational；

bucket 内各项按 exact dyadic 求和；

最后只舍入一次到 binary64；

family squared norm 为所有坐标平方的 exact dyadic sum；

norm 为 correctly rounded binary64 square root；

每个归一化值为 exact x/norm 后舍入一次；

C02 norm side feature 是 correctly rounded log1p(norm)。

log1p 等非基础函数需要明确的 correctly-rounded 实现。MPFR 的公开合同是“仿佛以无限精度计算后再按指定模式舍入”；独立 provider 可用 MPFR 与另一套 interval/ball arithmetic 实现交叉验证。
GNU MPFR Library
+2
Arb
+2

因此，现有的：

CPython
NumPy float64
single-thread
einsum optimize=false

可以保留为一个运行 profile，但不应被当成跨语言数学合同。

2.7 Column order
C02 / C05

对 family 按 F01→F07：

for each active numeric ID in canonical order:
    NUM_VALUE
    NUM_MISSING

CAT_HASH_BUCKET 0..16383

for each ngram namespace in canonical order:
    NGRAM_BUCKET 0..4095

FAMILY_NORM

C02 的 FAMILY_NORM 值是 log1p(norm)。

C05 建议使用 raw norm。若本地原设计意图也是 log1p(norm)，必须在版本发布前明确，不能由 provider 推断。

无额外 ngram namespace 时：

ncols
C02,C05
	​

=2N+7(16384+4096+1)=2N+143367
C03 / C04

顺序相同，但没有 family norm：

ncols
C03,C04
	​

=2N+143360
C01

C01 不应被强行装进普通 float CSR。它应接收 canonical atom stream：

CAT_EXACT_PRESENCE
CAT_CONTEXT_STATE
NUM_EXACT_EQUALITY
NGRAM_BUCKET_PRESENCE

atom 按：

kind rank
family rank
canonical identity bytes
state bytes

排序。

2.8 C01 建议的 exact contract
候选

calibration 中全部 exact categorical token presence；

schema 声明为 single-valued 的 categorical contexts；

每个 active numeric identity 的 calibration-seen exact values 与 MISSING；

TOP256 token 的 unordered two-way conjunction。

推荐把 TOP256 token 定义为：

exact categorical token presence；

direct ngram bucket presence；

不包括 numeric equality，也不重复加入 synthetic numeric missing。

TOP256

support 定义为 calibration 中“至少出现一次”的 row 数，而不是 count 总和。

排序：

descending row support
then ascending canonical atom bytes

取前 256。并列不读取 label。

最多产生：

(
2
256
	​

)=32640

个 conjunction candidates。

Context mapping

仅对 schema-declared single-valued context：

无值：MISSING；

一个 distinct value：该 32-byte digest；

calibration 未见的 holdout value：OTHER；

超过一个 distinct value：若 schema 声明 singleton，失败 F009_CONTEXT_CARDINALITY。

规则比较

Balanced accuracy 应使用 exact confusion counts 计算，而不是 binary64。Balanced accuracy 的标准定义是各真实类别 recall 的宏平均。
scikit-learn

比较次序建议冻结为：

1. larger exact balanced accuracy
2. lower complexity tuple
3. lexicographically smaller UTF-8 rule serialization

推荐 complexity tuple：

(number of atomic predicates,
 number of explicit non-default branches,
 serialized byte length,
 rule-kind rank)

UTF-8 serialization 应只使用 ASCII 子集、hex identity 和规范化 rational n/d，避免 locale 与 Unicode 差异。

holdout 中不允许：

新增 mapping entry；

重新选择 orientation；

合并 OTHER；

重新计算 TOP256；

重新比较规则。

2.9 Sparse artifact 与 hash preimage

使用 canonical CSR：

indptr[0]=0；

每行 column index 严格递增；

不允许 duplicate index；

不保留 explicit zero；

所有 zero 先规范成 +0.0 再省略；

不允许 NaN/Inf；

indptr 使用 uint64 big-endian；

column indices 使用 uint32 big-endian；

values 使用 8-byte binary64 big-endian。

SciPy 所称的 canonical CSR 同样要求行内 indices 已排序且没有 duplicate entries。
SciPy 文档

建议 matrix bytes：

MAGIC
FORMAT_VERSION
MODEL_ID
SPLIT_ID
NROWS
NCOLS
NNZ
ROW_MANIFEST_HASH
COLUMN_MANIFEST_HASH
PREPROCESS_HASH
INDPTR_BYTES
INDEX_BYTES
VALUE_BYTES

最终：

artifact_hash =
SHA256(
  "W025-MI/ARTIFACT/v1\0" ||
  LP64(schema_manifest_bytes) ||
  LP64(row_manifest_bytes) ||
  LP64(column_manifest_bytes) ||
  LP64(preprocess_manifest_bytes) ||
  LP64(matrix_bytes)
)

不要直接 hash：

pickle；

.npz；

raw Protobuf；

provider 自己生成的 JSON。

Protocol Buffers 官方明确说明 deterministic serialization 并不等于跨语言、跨版本 canonical serialization，因此不适合作为长期 artifact 指纹的未加约束 preimage。
协议缓冲区
+1

Deterministic CBOR 可以用于 manifest，但应采用窄 profile：固定 array 结构、无不定长项、整数 canonical、binary64 作为 8-byte byte string，而不是依赖编码器自行选择浮点宽度。RFC 8949 提供了 deterministic encoding 规则。
RFC Editor

更简单的选择仍是上述固定 TLV。

2.10 最强替代方案
替代 A：纯静态 universe

适用条件：

route/schema 完整且有限；

route binding 已验证；

schema 规模小；

schema 为 calibration 未见 numeric 定义了外部 center/scale；

项目愿意放宽“holdout-only numeric 必须失败”。

当前 packet 不满足最后一项，因此纯静态展开主要制造全 missing columns。若 active numeric 有很多，missing indicators 还会使 CSR 接近稠密。

替代 B：纯 calibration-derived universe

适用条件：

只做一次封闭批次；

允许所有 holdout-only numeric 令整批失败；

不声称跨 route/schema 迁移；

collector admission 已由其他机制验证。

它的优点是列少、实现简单；缺点是 calibration 中出现的错误 identity 会被当成合法身份。

替代 C：exact categorical dictionary

对本次只有 400 calibration rows 的资格实验，可以把 calibration-seen exact token IDs 直接按 bytes 排成稀疏列，并设置 context-aware OTHER。

优点：

无 hash cancellation；

可解释；

provider 更容易逐列比对。

缺点：

维度由 calibration token cardinality 决定；

holdout-only exact token 只能进 OTHER；

改变 C02/C05 的既有 signed-hash 定义。

最合理的使用方式是：作为隐藏 shadow detector 或差分 golden，不直接替换 C02/C05，除非正式版本允许改模型。

替代 D：一个 compiler + 一个小 verifier

一个 provider 生成完整 artifact，另一个只独立检查：

identity framing；

hash；

column order；

selected rows；

CSR canonicality；

随机抽样重算。

成本更低，但无法发现两个语义层共同遗漏。对于正式资格实验，它弱于两个完整独立 provider。

推荐的强中心边界

无需让两个 provider 各自训练五个模型。

更简单、也更稳的是：

两个独立 provider 只负责生成 C01 atom stream 与 C02–C05 matrices；

bytes/hash 完全一致后；

一个冻结的 trainer 读取 canonical artifact；

统一训练并提交 holdout predictions。

这样把跨实现浮点问题限制在 input compiler，不再为 logistic gradient、tree tie、kNN distance 各复制一套实现。

2.11 两个 provider 的 goldens、holdbacks 与验收
独立性要求

两个 provider：

不共享 feature compiler 代码；

不共享生成后的 column manifest；

不共享 intermediate matrix；

最好使用不同语言和不同 parser；

至少一方不依赖 NumPy/SciPy 构建矩阵；

numerical oracle 最好一方用 MPFR，另一方用独立 ball/interval 实现；

允许共享公开 spec、count table 和标准 test vectors。

build metadata 可以进入外部 receipt，但不进入 classifier artifact。

Public goldens

至少包括：

identity framing

字段包含 NUL；

可变长度字段；

ordered CTX2 交换；

channel/expected_channel 交换。

hash KAT

完整 preimage hex；

digest；

bucket；

sign；

一对已知同 bucket、反 sign token。

count aggregation

一行 count=2；

两行 count=1；

两者输出完全相同；

254、255、256、超大 count。

rational→binary64

0；

负数；

1/10；

两个 binary64 中点；

subnormal；

overflow failure；

-0 canonicalization。

quantile

odd/even sample；

averaged_inverted_cdf 的平均分支；

IQR=0。

missing

observed exact 0；

absent；

两者 value 相同但 missing bit 不同。

CSR

无序 insertion；

duplicate coordinate；

explicit zero；

canonical output hash。

C01

TOP256 tie；

pair ordering；

equal balanced accuracy；

complexity tie；

UTF-8 serialization tie。

route-aware ngram

同 bucket、不同 namespace；

route 缺失的预期失败。

holdout drift

schema-valid 但 calibration-unseen numeric；

必须返回同一 failure code。

Hidden holdbacks

应由第三套 fixture generator 产生，且不复用 provider 代码，覆盖：

predictor row 的随机 permutation；

sparse insertion permutation；

adversarial bucket collision/cancellation；

exact normalization 边界；

log1p(norm) rounding 边界；

multi-valued categorical context；

holdout-only categorical value；

all-missing family；

multiple ngram namespaces；

low-entropy manifest dictionary attack；

opaque row-order tie；

noncanonical rational 与 duplicate numeric。

Failure codes

建议固定第一错误优先级：

Code	含义
F001_UNSUPPORTED_VERSION	spec/schema/artifact 版本不支持
F002_FORBIDDEN_FIELD	predictor 中出现 sidecar/path/provenance/debug 等禁字段
F003_ROW_MANIFEST_MISMATCH	row membership、split 或 ordinal 不符
F004_ROUTE_BINDING_UNRESOLVED	无法把 row 唯一绑定到语义 namespace
F005_SCHEMA_IDENTITY_VIOLATION	calibration 或 holdout identity 不在 allowed schema
F006_NONCANONICAL_RATIONAL	denominator、gcd、zero form 等不规范
F007_DUPLICATE_NUMERIC	同 sample 同 numeric identity 多行
F008_INVALID_COUNT	count 非正或编码不规范
F009_CONTEXT_CARDINALITY	singleton context 出现多个 distinct values
F010_HOLDOUT_NUMERIC_DRIFT	holdout 出现 calibration 未激活 numeric identity
F011_NONFINITE_FLOAT	overflow、NaN 或 Inf
F012_COLUMN_MANIFEST_MISMATCH	列 identity/order/hash 不一致
F013_NONCANONICAL_CSR	duplicate、乱序、显式零、错误 endian
F014_PROVIDER_DIVERGENCE	两 provider artifact bytes 不同
F015_EARLY_LABEL_ACCESS	universe/preprocess 冻结前读取 label
F016_HOLDOUT_RESELECTION	holdout 后扩列、重新拟合或重选规则

同一 fixture 同时有多个错误时，provider 必须按 code 顺序报告最小 code，避免一个实现先发现 A、另一个先发现 B。

验收顺序

冻结 spec、schema、membership、row order、可选 hash-key commitment。

隔离 labels；provider 环境中不存在 label path 或 capability。

两 provider 跑 public goldens。

两 provider 跑 hidden holdbacks。

独立生成 calibration preprocessing manifest。

比较 active numeric list、quantiles、TOP256、column manifest 的 bytes。

编译 calibration matrices/atoms，并逐字节比较。

predictor 全部冻结后揭示可选 hash key。

用冻结 P1 编译 fresh holdout。

任一 numeric drift 立即令本次资格失败，不继续打分。

provider bytes 完全一致后，接受一个 canonical artifact。

向单一 trainer 释放 calibration labels。

固定并提交五个模型及 holdout predictions。

evaluator 最后打开 holdout labels。

不允许任何 holdout-based rerun、reselection 或 applicability removal。

3. Exact machine-contract decisions still required

以下不是实现细节，而是会改变最终 bytes 或结果的未冻结合同。

3.1 Route 与 typed CTX2 的关系

必须回答：

typed CTX2 是否已经包含 route semantic namespace？

route 是 predictor identity 的组成部分，还是仅为 admission metadata？

不同 route 的 ngram bucket 语义是否相同？

route-specific columns 是否会把 treatment assignment 本身编码为 predictor？

这是当前最优先 blocker。

3.2 C01 的 token 范围

必须冻结 TOP256 是否包括：

exact categorical token；

ngram bucket；

categorical missing；

numeric missing。

建议只包括前两者，missing 已由 context/numeric rule 覆盖。

3.3 C01 support 的精确定义

题目给出“总10、每预测类5”，但尚未定义 support 是：

predicate-true coverage；

branch coverage；

correctly predicted rows；

还是规则输出每一类的 row 数。

建议：

presence/equality/conjunction 的显式 trigger branch 至少覆盖 10 rows；

对规则实际输出的每个 class，至少有 5 calibration rows 被分配到该 class；

context mapping 中不足 support 的 calibration states 合并到 OTHER/default；

support 与 mapping selection 在 label 释放后完成，candidate universe 不变。

3.4 C05 family norm

必须选定：

raw norm；

log1p(norm)；

或完全不追加。

根据当前文字，raw norm 最直接；C02 才明确是 log1p(norm)。

3.5 Hash cancellation 的资格解释

必须写进成功判据：

C02/C05 negative 不能单独作为无泄漏证据；

C01 exact 与 C03/C04 OR 是 mandatory controls；

若最终资格声明要求每个模型自身 collision-safe，则必须修改 C02/C05，加入 unsigned occupancy、第二独立 hash 或 exact dictionary。

这是数学限制，不是 provider 工程质量问题。

3.6 Trainer 合同

即使 matrix bytes 完全一致，端到端输出还需要冻结：

C02

L2 λ；

intercept；

intercept 是否 regularize；

class weighting；

initialization；

Armijo c1、shrink factor、初始 step；

stopping condition；

maximum iterations；

gradient reduction order。

C03/C04

impurity；

threshold midpoint；

min leaf/support；

equal-gain tie order；

categorical/numeric column tie order；

depth 的定义。

C05

uniform 或 distance-weighted vote；

squared distance 或 sqrt distance；

equal-distance neighbor tie；

class-vote tie；

calibration row ID tie-break。

这些不会改变本报告对 universe 的推荐，但会改变最终 C01–C05 predictions。

4. Counterexamples and removable mechanisms
4.1 最小反例
删除的机制	最小构造	后果
numeric missing indicator	class A 中 identity 缺失；class B 中 observed exact 0	两者 value 都是 0，泄漏被抹掉，假绿
holdout numeric drift failure	calibration 只有 N0；holdout 才出现强预测 N1	静默丢弃导致漏检；扩列导致 holdout-dependent universe
typed context/order binding	同一 value digest 分别位于 argv[0] 与 argv[1]，标签依赖位置	若排序或只 hash value，两行同向，复现 ordered-argv 假绿
OR occupancy	t1、t2 同 bucket、反 sign，同时仅在一类出现	signed sum=0；用 sum!=0 判 presence 会称其 absent
aggregate-before-transform	同一 logical token 一方输出 count=2，另一方输出两行 count=1	log(3) 与 2log(2) 不同，provider/collector fragmentation 分叉
quantile method pinning	calibration values [0,1,2,100]	不同 quantile method 得到不同 Q25/Q50/Q75、不同 matrix
exact rational rounding	rational 恰在相邻 binary64 中点	decimal parsing、双重舍入或非 ties-even 实现产生不同 bytes
+0 canonicalization	一个 provider 产生 -0.0，另一个 +0.0	数值比较相等但 SHA-256 不同
CSR canonicality	同一逻辑坐标以不同 insertion order 或 duplicate entries 写入	dense matrix 相同，artifact hash 不同
length-prefixed preimage	(ctx="ab",channel="c") 与 (ctx="a",channel="bc")	裸拼接同 preimage，两个 identity 被错误合并
route-aware ngram	route R0 与 R1 的 bucket 17 表示不同 collector 语义	直接合并制造假关联或抵消
label-bearing manifest hash	case/label 只有几个候选值，向 provider 暴露其 hash	provider 可离线枚举候选，而 SHA 并不提供低熵隐藏
fixed row manifest	provider A 按文件名排，B 按 opaque ID 排；kNN 距离或 tie 相同	predictions 可因 reference-row tie 顺序分叉
calibration-only TOP256	用 holdout predictor support 重新排序	holdout distribution 参与候选选择，资格无效
4.2 应删除的形式复杂度
应删除

静态展开全部 calibration 未见 numeric columns；

把 route ID 直接作为 one-hot classifier feature；

在 matrix preimage 中加入 path、mtime、provider build；

用 raw Protobuf、pickle 或 .npz bytes 做长期 canonical hash；

为两个 provider 各复制一整套 model trainer；

把 signed bucket value 非零当 presence；

provider 自己选择 quantile method；

runtime 调用未冻结的 log1p 生成 count transform；

为“看起来更安全”重复 hash 同一 artifact 多次；

把 collision/provenance diagnostics 喂进 classifier。

条件性保留

HMAC hash key：只有 treatment 能针对已知 bucket 自适应造 token 时保留。

exact-dictionary shadow：若 C01/C03/C04 已足以承担 collision control，可仅在 hidden holdbacks 中使用。

deterministic CBOR：团队已有成熟、严格 profile 的实现时可用；否则固定 TLV 更小、更容易双实现。

5. The single next local experiment that best distinguishes alternatives
G-MI-01 — Pre-label compiler duel

现在不应先跑 3200-row 全实验。最有区分力的下一步是：

用真实的 400-row T-calibration predictors，但完全不开放 labels，再附加一个隔离的 adversarial micro-fixture，令两个独立 provider 同时运行 A、B、H 三种 universe 模式。

真实部分

对 400 calibration predictor rows，分别计算：

S_N = static schema numeric identities
C_N = calibration observed numeric identities

只比较：

C_N \ S_N
S_N \ C_N
canonical order
preprocess bytes
matrix bytes

不报告模型效果。

判定：

C_N \ S_N 非空：static/hybrid 正确阻断；说明 route/schema 或 collector admission 尚未闭合。纯 B 即使生成矩阵，也只能算机械编译成功。

S_N \ C_N 很大：纯静态正在制造无训练意义的 missing 列，H 更优。

两 provider 对 H 的 bytes 不同：先修 machine contract，不进入 3200 run。

H bytes 一致且 route binding 有效：才进入正式 fresh holdout。

隔离 micro-fixture

同一次实验包中加入以下独立 cases：

schema-invalid calibration numeric；

schema-valid 但 calibration-unseen 的 synthetic holdout numeric；

ordered CTX2/channel swap；

known same-bucket opposite-sign category pair；

count=2 与 count=1+1；

observed zero 与 missing；

exact rational midpoint；

IQR=0；

two ngram namespaces sharing bucket 17；

shuffled predictor-row and sparse insertion order；

explicit -0.0 attempt；

forbidden sidecar field。

预期结构性结果：

A/H 在 case 1 返回 F005，B 会接受，从而直接展示 B 的语义弱点；

三种模式在 case 2 都必须返回 F010；

case 3 必须产生不同 identity；

case 4 中 C02/C05 signed bucket 可为 0，但 C03/C04 presence 必须为 1；

case 5、10 必须得到相同 artifact hash；

case 9 在缺少 binding 时必须返回 F004；

两 provider 对所有 valid case 的 bytes 完全一致，对 invalid case 的 primary code 完全一致。

这一个实验同时区分：

static schema 是否真实可用；

calibration-only 是否掩盖 admission 错误；

hybrid 是否可落地；

两 provider 是否真的独立一致；

当前 float/hash/presence 合同是否足够。

它不需要 label，不需要 2400 fresh holdout，也不会消耗正式 holdout。

6. Missing material that could materially change the answer

只有以下材料会实质影响最终 machine contract：

typed CTX2 是否已经绑定 route semantic namespace。
若没有，当前 ngram tuple 不足以实现 route-aware direct columns，正式资格必须阻断。

每个 categorical context 的 schema cardinality。
没有 SINGLE/MULTI 声明，C01 context total mapping 不能唯一解释。

C01 support、default、OTHER 与 label-tie 的正式定义。
这不改变输入 universe 选择，但会改变最终 C01 rule。

C05 norm 到底是 raw 还是 log1p。
会直接改变列 bytes 和欧氏距离。

route-specific ngram namespace 数量。
会改变列数和资源上界。

端到端是否要求两个 provider 连 trainer 结果也 bitwise 一致。
若只要求输入一致，采用单一 frozen trainer 最简单；若要求两个完整 trainer 一致，还必须补齐第 3.6 节全部 reduction、tie 与 stopping 合同。

在不获得这些材料的情况下，仍然可以确定：H 是当前最强输入架构；route binding 未完成前不得给出完整资格通过；单一 signed hash 的负结果不得被解释为无泄漏。

## Visible source links

- [scikit-learn +1](https://scikit-learn.org/stable/modules/feature_extraction.html?utm_source=chatgpt.com)
- [NumPy](https://numpy.org/doc/2.1/reference/generated/numpy.quantile.html)
- [NIST计算机安全资源中心 +1](https://csrc.nist.gov/pubs/fips/180-4/upd1/final?utm_source=chatgpt.com)
- [scikit-learn](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.RobustScaler.html)
- [Oracle 文档 +1](https://docs.oracle.com/javase/specs/jvms/se17/html/jvms-2.html)
- [GNU MPFR Library +2 Arb +2](https://www.mpfr.org/mpfr-current/mpfr.html?utm_source=chatgpt.com)
- [scikit-learn](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.balanced_accuracy_score.html)
- [SciPy 文档](https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.csr_matrix.html?utm_source=chatgpt.com)
- [协议缓冲区 +1](https://protobuf.dev/programming-guides/serialization-not-canonical/)
- [RFC Editor](https://www.rfc-editor.org/info/rfc8949/?utm_source=chatgpt.com)

