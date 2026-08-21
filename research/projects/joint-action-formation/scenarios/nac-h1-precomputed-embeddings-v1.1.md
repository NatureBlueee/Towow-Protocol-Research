# Scenario：NAC E-H1′ 预计算嵌入与原生信息条件判别沙箱

Contract：`SCN-NAC-H1-PRECOMPUTED-EMBEDDINGS / v1.1`

状态：`VALIDATED` 候选，等待精确激活投影。

这个版本保留 v1 的本地、可逆、非现实机制研究边界，但修正一手来源复核发现的公平性错误：
NAC、vec2vec、Procrustes 与共享参考编码器使用不同的原生信息条件，不再强制 same-K。

所有方案仍共享同一 test truth、候选池、关键切片与指标；同时分别绑定其数据和训练条件，
并统一核算完整生命周期资源。只有满足 schema 的五模型预计算 embedding 包才能进入
E-H1′；当前工具与合成回归通过不构成机制证据。

v1 保留为未实际开 batch 的历史激活快照，不被覆写。
