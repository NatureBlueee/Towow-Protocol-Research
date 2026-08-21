# NAC E-H1′ 现成方案核验（2026-07-28）

## 作用域与证据边界

本文件只回答 `E-H1-PRIME → MC-NAC-ANCHOR` 在开跑前必须面对哪些现成方案，以及它们
覆盖了什么、没有覆盖什么。它不判断 NAC 的前缀、方向性、自描述、迁移、M3 路由或完整
Agent 关系形成。

本轮将“论文标识存在”“原文声称”“已经独立复现”严格分开：

- **原始页面已核验**：Relative Representations 的 ICLR 2023 会议信息、arXiv 正文与
  作者源码；vec2vec 的 arXiv 正文；Latent Space Translation 的 NeurIPS 2023 页面；
  2025 Procrustes 预印本页面。
- **论文作者报告，未独立复现**：下文列出的实验数值、跨模型泛化和训练稳定性。它们只能
  决定基线与反例，不能作为 NAC 或替代方案已经在通爻分布上有效的证据。
- **系统构造基线**：“stable Schema + 共享参考编码器”不是一篇论文的专名，而是为了检验
  “是否根本需要跨空间机制”而构造的强中心对照。

本轮使用的主要一手入口：

- Relative Representations：
  [ICLR 2023](https://iclr.cc/virtual/2023/oral/12532)、
  [arXiv:2209.15430](https://arxiv.org/abs/2209.15430)、
  [作者源码](https://github.com/lucmos/relreps)；
- vec2vec：
  [arXiv:2505.12540](https://arxiv.org/abs/2505.12540)、
  [作者源码](https://github.com/rjha18/vec2vec)；
- Latent Space Translation：
  [NeurIPS 2023](https://neurips.cc/virtual/2023/poster/70426)；
- Procrustes：
  [arXiv:2510.13406](https://arxiv.org/abs/2510.13406)。

## 现成方案与覆盖判断

### 1. Relative Representations（ICLR 2023）

原论文不是泛泛谈“相对表示”，而是给出了与 `MC-NAC-ANCHOR` 几乎同构的坐标：

\[
r_x =
(\operatorname{sim}(e_x,e_{a_1}),\ldots,
 \operatorname{sim}(e_x,e_{a_K}))
\]

锚点顺序固定；论文默认以 cosine similarity 取得对旋转、反射和缩放的不变性。跨域或跨
模态场景使用具有对应关系的 **parallel anchors**。作者同时明确写出前提：不同模型需要对
相近现象建模，其潜空间近似由保角变换关联；这不是对任意异构编码器均成立的定理。

原文实验还给 E-H1′ 两个直接约束：

- FastText 与 Word2Vec 实验使用约 20K 共享词、300 个随机 parallel anchors；
- 相对表示的 MRR 为 0.94–0.98，但邻域 Jaccard 只有 0.34–0.39。前者支持列表顶部
  排序可恢复，后者同时保留了“精确邻域仍显著不同”的负结果。

对 `MC-NAC-ANCHOR` 的覆盖是 **PARTIAL，但覆盖技术内核**：

- 已覆盖：公共锚点、正典顺序、逐锚点相似度坐标、无需额外训练的跨空间比较；
- 未覆盖：通爻的有向 Intent—画像 ground truth、五种以上现代文本 embedding、跨语言
  最坏切片、候选池中的 `Recall@100`、前缀生命周期与版本治理；
- 不能外推：论文的“zero-shot”不等于“无协调”。parallel anchors 本身就是共享对应与
  正典顺序；锚点选择影响表达能力；
- 研究含义：E-H1′ 不能再把“锚点相似度形成跨空间坐标”当成 NAC 新原理。若实现只复刻
  上式，NAC 在坐标层的独立贡献为零；剩余价值必须来自目标分布适用性或部署/治理差异。

这是对 NAC 独立价值的第一强反例。

### 2. vec2vec（arXiv:2505.12540，NeurIPS 2025）

论文题为 *Harnessing the Universal Geometry of Embeddings*。它不是依赖 paired data 的
普通映射：作者声称在不知道源 encoder、没有成对样本和预定义匹配集的情况下，从两个
embedding 分布学习翻译。其结构含各空间 input/output adapters 与共享 latent backbone，
损失由 adversarial、reconstruction、cycle consistency 和 vector-space preservation 组成。

这纠正了此前实验设计中的两个错误：

1. **不能把 vec2vec 描述成必须取得与 NAC 相同的共享语义样本。** 原文默认训练使用从 NQ
   抽取的两组互不相交的 100 万条 64-token 序列 embedding；它需要的是大规模同类分布样本，
   不是 parallel anchors。
2. **不能未经测量就假定它必然产生模型对数量爆炸。** 论文架构具有共享 latent backbone
   和空间专用 adapters；多模型能否复用 backbone、增加一个模型需要训练多少组件，是应测
   的生命周期变量，不是 NAC 预先获胜的理由。

作者报告覆盖多种骨干、维数和训练数据的模型面板，并在部分模型对达到很高的 cosine /
matching 表现；但原文也保留了对 E-H1′ 更重要的负面信息：

- 训练依赖 GAN，作者明确因不稳定而从多个初始化中选择最佳模型；
- 性能具有明显模型对和分布依赖，跨骨干及跨模态更难；
- 其主评测是向目标空间真值向量翻译、top-1 与 mean rank，不等同于有向 Intent—画像
  `Recall@100`，不能直接借用其数值宣布“发现级召回已解决”。

对 `MC-NAC-ANCHOR` 的覆盖是 **PARTIAL，且比先前判断更强**：

- 已覆盖：无 paired data 的跨模型翻译、可共享的 latent 表示、异维 encoder adapter；
- 未覆盖：零训练/小锚点预算、正典前缀、可离线计算的公共坐标、通爻的目标分布与版本治理；
- 公平比较：不强行统一 `K`。应让 NAC 使用 parallel anchors，让 vec2vec 使用其原生
  unpaired corpus，再共同核算语料获取、encoder 调用、训练计算、best-of-seeds、存储、
  新模型接入和版本迁移成本；
- 研究含义：若 vec2vec 在真实可承担的总成本内达到更高最坏切片 Recall，且 adapter
  扩张可控，它会同时击穿 NAC 的精度优势和“避免两两映射”的生命周期叙事。

这是对 NAC 独立价值的第二强反例。

### 3. 闭式语义对齐与 Orthogonal Procrustes

这里要区分两个相邻但不同的来源。

**Latent Space Translation via Semantic Alignment（NeurIPS 2023）** 报告可用标准、闭式
代数过程直接估计两个潜空间间的变换，无需再训练 stitching layer；实验覆盖不同训练、
领域、架构和部分跨模态 stitching。它说明“训练一个复杂 translator”与“改成相对坐标”
并非唯二选择。

**When Embedding Models Meet: Procrustes Bounds and Applications
（arXiv:2510.13406）** 进一步把对应样本上的 Orthogonal Procrustes 作为 embedding
模型互操作的后处理：估计正交变换，把源模型输出放到目标空间，同时保留源空间内部几何。
当前只核验到预印本原始页面，尚无本工作区独立复现或同行评审状态证据。

对 `MC-NAC-ANCHOR` 的覆盖是 **PARTIAL，且是不可遗漏的低复杂度强基线**：

- 已覆盖：有对应样本时的闭式/低复杂度跨空间映射与几何保持；
- 未覆盖或待实测：无需目标空间、单一公共坐标、异维处理、多模型统一接口、通爻有向
  Intent—画像与跨语言最坏切片；
- 公平比较：在同一 parallel correspondence 池上比较 NAC 与 Procrustes 的样本效率，
  再分别报告 full-pair、hub-and-spoke 和新增版本三种部署形态；
- 研究含义：若 hub Procrustes 在很小 correspondence 预算下已跨过 80% 门槛，NAC 必须
  证明其消除 hub 或减少迁移成本的净价值，而不能靠“无需神经网络训练”获胜。

### 4. stable Schema + 共享参考编码器

这是一个刻意构造的消融基线，不是跨模型对齐：所有节点保留本地模型，但把公开的稳定
Schema 字段同时送入一个冻结参考 encoder，并只在参考空间建立发现索引。它直接消除了
跨空间问题。

对当前完整环境前提的覆盖是 **条件性 COMPLETE / PARTIAL**：

- 若允许共同调用或本地部署一个参考 encoder，且单点依赖、版本治理、隐私与成本可接受，
  它对“建立统一发现空间”可以是 **COMPLETE**，不是 PARTIAL；
- 只有当“任何共享 encoder 均不可接受/不可达”被明确登记为硬前提时，它才因违反环境前提
  而不适用；“节点有自己的模型”本身并不推出“不能额外运行参考模型”；
- 公平比较必须冻结 encoder 的模型与版本、query/document 指令、池化、归一化、维数、
  tokenizer、reranker 和升级策略；
- 研究含义：若该臂在真实治理约束内更准、更便宜，最好的结论应是采用中心基线并停止 NAC
  坐标建设，而不是为了保持异构性继续复杂化。

这是对 NAC 独立价值最强的系统级反例。

### 5. stable Schema + lexical / learned-sparse / reranker

“自然语言 + stable Schema”本身只是交换表示，不是完整检索算法。若不冻结候选生成、
排序模型、预算和版本，就没有可以与 NAC 比较的实验臂。

至少拆成：

- 结构化字段上的 lexical 候选生成；
- 固定模型与版本的 learned-sparse 候选生成；
- 上一节的共享参考 dense embedding；
- 可选的固定预算 reranker，且所有允许重排的候选臂取得相同候选窗口和调用预算。

否则“自然语言臂胜出或失败”无法定位到 Schema、检索器还是 reranker，也不能用于关闭
`MC-NAC-ANCHOR`。

## 被核验结果推翻的旧比较口径

以下口径不得进入 E-H1′ manifest：

1. **“NAC、vec2vec、Procrustes 获得相同数量共享语义样本才公平”——错误。** 三者原生
   信息结构不同：NAC/Procrustes 需要 correspondence，vec2vec 明确以 unpaired distribution
   训练。公平对象应是能力边界与总资源账，不是人为统一一个不适用的 `K`。
2. **“vec2vec 是普通模型对专用翻译器”——证据不足。** 其共享 latent backbone 与
   space-specific adapters 至少使线性 onboarding 成为竞争解释，必须实测而非先验排除。
3. **“共享参考编码器只覆盖部分要求”——取决于硬前提。** 若共享 encoder 可接受，它可能
   完整消除坐标问题；必须先证明 A3 排除了它，不能把机制偏好写成环境事实。
4. **“论文高 MRR/top-1 已证明通爻 Recall@100”——错误。** 任务、候选池、方向和标签均
   不同，只能作为方法可行性与失败切片线索。

## E1 公共数据候选

### 纳入门槛

这里的“足以形成 E1”不是指数据可以被读进 evaluator，而是它至少同时给出：

- 可识别的有向 query/SEEK 与 candidate/OFFER；
- 独立于受测 embedding 的相关性或匹配标签；
- 每个 query 大于 100 的可评价候选池，足以解释 `Recall@100`；
- 可预注册的多语言或跨语言切片；
- 数据内容与代码的许可、版本和来源可追踪。

本轮只核验公开的一手论文、机构仓库和仓库许可页；**没有下载数据，也没有复现任何统计或
baseline**。下列数字均为数据发布者报告。

### 候选 A：Amazon Shopping Queries / ESCI

一手来源：
[Amazon Science 仓库](https://github.com/amazon-science/esci-data)、
[数据集论文 arXiv:2206.06588](https://arxiv.org/abs/2206.06588)。

- **fit**：真实用户购物 query 有明确方向，product title/description/bullet points 可作为
  最接近 OFFER 的公开文本；人工 ESCI 标签区分 Exact、Substitute、Complement、
  Irrelevant；包含英语、日语和西班牙语。发布者报告大版本有 130,652 个 query、
  2,621,738 个 query-product judgement。
- **gap**：每个 query 只发布“最多 40 个”潜在结果，平均深度约 20，不能评价
  `Recall@100`。把同 locale 全商品强行加入候选池会产生大量**未判定** item，不能当负例；
  三个 locale 是分别采样的 query，不是已对齐的跨语言 SEEK；商品相关性也没有主体能力、
  可用性、授权、互补形成或双向认领。
- **license**：官方仓库标注 Apache-2.0；正式使用仍须冻结具体数据文件版本和仓库
  `LICENSE`，不能只引用论文许可。
- **是否足以形成 E1**：**否**。可形成 `E1-ESCI-PROXY`，用于验证 SEEK→item 方向字段、
  E/S/C/I 多值标签、三语言分层及 evaluator 的 query/candidate 隔离；不能运行历史
  `Recall@100` 主门，也不能据此判断 Agent 画像匹配。

ESCI 的价值恰好来自它暴露的缺口：最像 OFFER 的公开集没有足够深的已判定候选池。

### 候选 B：MIRACL

一手来源：
[项目仓库](https://github.com/project-miracl/miracl)、
[TACL 2023 论文](https://aclanthology.org/2023.tacl-1.63/)。

- **fit**：发布者报告 18 种语言、78K query、726K 以上人工 relevance judgement；每种
  语言的 Wikipedia passage corpus 从 131,924 到 32,893,221 条，天然远大于 100，
  适合压力测试全库检索、最坏语言切片和不同模型空间的 `Recall@100`。
- **gap**：MIRACL 明确是**同语种检索**——query 与 corpus 使用相同语言，不是跨语言
  query/candidate 对齐；candidate 是知识 passage，不是 OFFER、画像或可行动主体；qrels
  的信息需求相关性不能替代“此主体能与该 SEEK 形成价值”的标签。
- **license**：项目仓库标注 Apache-2.0，TACL 论文为 CC BY 4.0；语料来自各语言
  Wikipedia dump，不能把仓库代码许可自动解释为对底层 Wikipedia 文本的重新许可。E1
  manifest 必须分别记录代码、qrels 与语料来源/归属要求。
- **是否足以形成 E1**：**否**。可形成 `E1-MIRACL-RETRIEVAL-CONTROL`，用于大候选池、
  多语言最坏切片和检索实现的阳性控制；不能关闭 SEEK→OFFER 假说，也不能把 monolingual
  multilingual 结果写成 cross-lingual 结果。

### 公共数据结论：当前没有单一可用 E1

截至本轮核验，**没有找到同时满足方向性 SEEK→OFFER、真实匹配标签、跨语言切片、
每 query 大于 100 个可判定候选和清晰许可的单一公开数据集**。

ESCI 与 MIRACL 也不能简单拼成正式 E1：

- 用 ESCI 的语义角色加 MIRACL 的候选规模，不会自动产生超过 100 个商品的人工 qrels；
- 用 MIRACL 的多语言标签替代 ESCI 的商品标签，会把任务从 OFFER 匹配改成知识检索；
- 机器翻译 query 或把未判定 corpus item 当负例，只能形成合成压力测试，不能冒充独立
  ground truth。

因此当前可诚实启动的是两个**非结论性控制**，而不是 NAC E-H1′ 主实验：

1. `E1-ESCI-PROXY`：验证有向字段、多值 relevance 与三语言 evaluator；
2. `E1-MIRACL-RETRIEVAL-CONTROL`：验证大候选池、多语言最坏切片和实现上限。

要形成正式 E1，还缺一个带明确许可的数据构造/标注 manifest：先冻结 SEEK 与 OFFER
语义、候选抽样框和每 query 超过 100 的判定池，再由独立于受测 encoder 的标注者给出
相关性；真实与翻译/合成部分必须分层。这个缺口是数据和测量条件缺失，不是 NAC 失败。

## 本轮综合判断

`prior_solution_review.disposition = EXTEND` 仍成立，但“未覆盖要求”进一步缩小。

现成研究已经覆盖：

- 公共平行锚点 + cosine + 固定顺序的相对坐标；
- 无 paired data 的可学习共享 latent / 跨空间翻译；
- 有 correspondence 时的闭式与正交变换；
- 允许共享 encoder 时直接消除异构坐标问题的系统路径。

仍未被现成结果直接关闭的是：

> 在有向 Intent—画像 ground truth、至少五种现代异构文本模型、跨语言和最坏模型对下，
> NAC 能否达到历史 80% `Recall@100` 门槛；并且在让各替代方案使用其原生信息条件后，
> 相对共享参考 encoder、unpaired vec2vec、hub/full-pair Procrustes 保留正的端到端净价值。

因此 E-H1′ 的公平性不应定义为“所有臂相同 `K`”，而应同时输出两类曲线：

1. **能力曲线**：Recall、最坏模型对、最坏语言/关系切片、失败 query；
2. **资源与治理曲线**：parallel/unpaired 数据需求、encoder 调用、训练与 best-of-seeds、
   在线计算、存储、组件数、新模型/新版本接入、迁移停机与单点依赖。

最强可证伪结果也更清楚了：

- 若 relative-coordinate 仅复现 ICLR 2023 方法且没有目标分布或生命周期增益，NAC 坐标
  内核没有独立研究贡献；
- 若共享参考 encoder 在可接受治理条件下覆盖需求，跨空间坐标问题无需解决；
- 若 vec2vec 的共享 backbone/adapters 或 hub Procrustes 在可承担成本内更准且扩张可控，
  “NAC 避免模型对爆炸”的主要部署理由不成立；
- 若所有表示在互补、长尾或复杂合取 Intent 上共同失败，应重构静态发现任务，把更多判断
  推迟到交互式边界发现，而不是继续优化坐标。
