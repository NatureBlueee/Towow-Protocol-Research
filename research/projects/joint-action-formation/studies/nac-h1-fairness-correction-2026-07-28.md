# NAC E-H1′ 激活后公平性修正

日期：2026-07-28

状态：`ACTIVE RESEARCH CORRECTION / NO MECHANISM RESULT`

## 修正内容

激活后的公开一手来源复核推翻了首个沙箱快照中的一项实验设计假设：

> 不能要求 NAC、vec2vec 与 Procrustes 获得相同数量的 shared semantic samples，作为
> “公平比较”的前提。

三种方法需要的信息结构不同：

- NAC / Relative Representations 使用按正典顺序组织的 parallel anchors；
- vec2vec 原论文默认从同类分布取得两组互不相交的大规模 embeddings，不需要 paired
  correspondences；
- Procrustes 依赖 source-target correspondences；
- 共享参考 encoder 通过统一重编码消除跨空间问题。

因此，首个已激活的
`SCN-NAC-H1-PRECOMPUTED-EMBEDDINGS / v1` 仍作为精确、不可悄悄改写的历史激活快照保留，
但其 same-K 条款不得用于构造输入或拒绝 vec2vec。尚未有任何实验 batch 使用该条款。

## 当前执行口径

后续 manifest 与 evaluator 必须：

1. 对所有方案冻结同一 test truth、候选池、语言/关系切片和指标；
2. 允许每个方案声明并哈希绑定其原生信息条件；
3. 分别报告能力曲线与资源/治理曲线；
4. 统一核算 corpus items、paired correspondences、encoder calls、训练计算、seed 或
   best-of-seeds、存储与传输、onboarding、adapter/mapping 数量、版本重算、双写与停机；
5. 不允许宏平均掩盖关键有序模型对和最坏切片失败。

## 它改变了什么

- vec2vec 从“同 K 的成对映射基线”升级为“无 paired data 的强反例”；
- “NAC 避免模型对爆炸”从预设优势降为必须测量的生命周期假说；
- 共享参考 encoder 在治理允许时可以完整消除坐标问题；
- E-H1′ 只有在原生信息条件和总资源账同时冻结后，才能产生可归因结果。

这项修正不支持或反驳 `MC-NAC-ANCHOR`，也不改变 H2–H8。
