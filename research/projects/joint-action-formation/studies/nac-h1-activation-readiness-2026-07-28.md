# Study — NAC E-H1′ 激活前判别力修复

日期：2026-07-28

状态：`HISTORICAL PRE-ACTIVATION NOTE / SUPERSEDED IN PART`

> 2026-07-28 激活后的一手来源复核纠正了本文件的 same-K 公平假设：vec2vec 原论文默认
> 使用两组不相交的大规模 embedding 分布，不要求 paired/shared semantic samples。
> 当前执行口径以
> `prior-art/nac-h1-existing-solutions-2026-07-28.md` 和
> `studies/nac-h1-fairness-correction-2026-07-28.md` 为准；本文件保留为激活前判断记录。

作用域：只研究 `E-H1-PRIME → MC-NAC-ANCHOR`。不测试 H2–H8，不改变
`MC-NAC-PREFIX`、`MC-NAC-DIRECTION`、`MC-NAC-SELF-DESCRIPTION` 或
`MC-NAC-MIGRATION`。

## 我们现在真正想理解什么？

不是“公共锚点能否产生一串数字”，而是：

> 在端点模型确实异构、又允许现成强方案获得公平资源的条件下，公共锚点相对坐标是否仍能
> 保住发现级 Recall，并因避免模型对专用映射而产生可归因的部署价值。

这一区分很重要。Relative Representations 已经覆盖锚点相似度坐标的技术内核；E-H1′
现在是一项目标分布扩展、最坏切片压力测试和替代方案比较，而不是从零证明一个新原理。

## 本轮直接观察

1. 原始 E-H1′ 已冻结：有向意图→画像标注集、至少五种异构模型、跨语言组、`K × 锚点选择
   × 前缀 × max/mean × vec2vec`，门槛为跨厂商 top-100 Recall 达到同厂商 80%。
2. 原始规格没有冻结数据规模、ground truth 产生方式、模型清单、训练/测试泄漏边界、
   80% 的分母、显著性、`K` 饱和定义或相同预算的会计口径。
3. “自然语言 + stable Schema”没有绑定候选生成器和排序器，当前不是可执行基线。
4. NAC 要求公共锚点、正典顺序、Schema 和版本，因此不是字面意义的“零协调”。它减少的
   是模型两两协商、共享内部维度或逐对重训。
5. 当前机器只发现一个完整缓存的 `BAAI/bge-m3`；Python 环境没有 torch、transformers、
   sentence-transformers、scikit-learn 或 faiss。不存在五模型本地运行条件。
6. 当前工作区没有可直接运行的 E-H1′ 实现、冻结标注集或五模型 embedding receipt。

第 5、6 项只说明当前运行条件不足，不说明机制不可行。

## 现成方案改变了什么？

详细核验见
`research/projects/joint-action-formation/prior-art/nac-h1-existing-solutions-2026-07-28.md`。

当前竞争解释是：

1. **NAC 有独立部署价值**：相对坐标在多模型和版本扩张时避免模型对映射爆炸，Recall 仍达
   原门槛；
2. **跨空间替代方案更好**：vec2vec 在原生 unpaired corpus 条件下，或 Procrustes 在
   correspondence 条件下显著更准，且完整生命周期成本仍可接受；
3. **强中心已经足够**：共享参考编码器 + stable Schema 更便宜、更准，异构公共坐标没有
   净新增价值；
4. **任务本身不可由静态表示充分承担**：所有表示在互补、长尾或跨语言切片上都失败，应把
   更多判断推迟到交互式边界发现，而不是继续换坐标。

## 激活前必须冻结的判别矩阵

### A. 数据与标签

- query 必须是 `SEEK`，candidate 必须是 `OFFER`；方向字段固定，不把方向性效果算给
  `MC-NAC-ANCHOR`；
- ground truth 独立于全部受测 embedding 模型；
- 真实语料与合成扩充分别报告，合成结果不能替真实结果；
- 按语义簇或关系族切分 train/dev/test，锚点选择与对齐训练不能看到 test 标签；
- 候选池必须显著大于 100，并冻结每个 query 的正例数，否则 Recall@100 不可解释；
- 单列语言、关系类型、陌生/长尾和复杂合取切片。

### B. 模型面板

- 至少五种模型，覆盖不同供应商、骨干、向量维数和语言强弱；
- 所有有序模型对 `A→B` 分别报告，不用一个宏平均隐藏结构性失败；
- 模型版本和原始 embedding receipt 固定；后续更换模型属于新运行。

### C. 表示与基线臂

1. 同模型原生 embedding 上界：`A→A`、`B→B`；
2. NAC / relative-coordinate：同一共享锚点文本，各模型本地计算相似度；
3. vec2vec；
4. Orthogonal Procrustes 或当前等价的几何保持对齐；
5. stable Schema + 共享参考编码器；
6. stable Schema + lexical / learned-sparse 候选生成；
7. 固定预算 reranker（若使用，所有候选臂获得同一预算）。

Relative Representations 不应被伪装成与 NAC 坐标内核完全独立的对照。它是本线要在新分布
上复现和扩展的直接先例。

### D. 公平预算（已由激活后复核纠正）

至少同时冻结并报告：

- 各方案的原生信息条件：NAC 的 parallel anchors、vec2vec 的两侧 unpaired corpus、
  Procrustes 的 correspondences、共享 encoder 的全量重编码；
- 语料条目、对应样本和 encoder 调用；
- 训练计算与 seed / best-of-seeds；
- 每模型 onboarding 计算；
- 每条 query / candidate 编码和检索计算；
- 存储与传输体积；
- 模型数增加时需要的 adapter / mapping 数量；
- 新版本加入时的重算、双写和停机成本。

公平不等于把不需要 correspondence 的 vec2vec 强塞进相同 `K`。所有方案必须共享同一
test truth、候选池、切片和指标，但可以使用原生信息条件；能力结果和完整资源账必须同时
报告。

### E. 指标与门

- 主指标仍保留原 `Recall@100` 与 80% 门槛；
- 在运行前冻结“同厂商分母”。建议同时报告
  `R_AB / R_AA`、`R_AB / R_BB` 和对称归一化值，不只留一个平均数；
- 门槛必须作用于预注册的关键模型对和关键切片；宏平均通过但关键对坍塌不能算通过；
- `K` 饱和需预先定义为连续扩容后的最小改进量，而不是看到曲线后决定；
- “显著低于强基线”需预先冻结 paired bootstrap / permutation 方法、置信区间和最小实质
  差异；
- 同时报告 Recall、最坏切片、每 query 延迟、候选编码成本和生命周期成本，不能只看一次
  离线排序。

## 当前判断

这段是激活前判断；用户随后已明确授权 `LINE-01-NAC` 进入 `ACTIVE`，但只激活可逆的
E0 数据工具、输入门禁和反例复核，不把缺失真实输入的 E-H1′ 本体伪装成已运行。

原因不是理论上证据不足——实验本来就是为了解决证据不足——而是当前输入还不足以让结果
支持或反驳冻结主张。现在开跑最可能得到一个无法归因的数字。

达到以下四项后，激活才具有信息增益：

1. 冻结可审计的数据/标签 manifest；
2. 冻结五模型与版本清单，并取得可运行环境或预计算 embedding receipt；
3. 把 Procrustes、共享参考编码器和可执行 stable-Schema 检索臂加入原生信息条件与完整
   资源账比较；
4. 冻结 80% 分母、关键切片、饱和与显著性规则。

## 这轮研究创造的新能力

- 能区分“相对坐标原理已存在”与“在通爻目标分布上仍有独立价值”；
- 能让强中心、成对对齐和 NAC 在同一资源会计下比较；
- 能在任何模型调用前发现数据规模、标签泄漏和平均数掩盖失败；
- 为下一轮输入 manifest 和 evaluator 提供了可直接实现的字段边界。

下一条最高价值行动是建立只接收预计算 embedding 的 E-H1′ 输入 manifest 与 evaluator，
先机械验证有序模型对、分母、切片和预算会计；这不会冒充真实模型实验。
