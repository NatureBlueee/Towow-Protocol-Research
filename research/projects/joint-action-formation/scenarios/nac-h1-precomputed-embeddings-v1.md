# NAC E-H1′ 预计算嵌入与强基线判别沙箱

Scenario：`SCN-NAC-H1-PRECOMPUTED-EMBEDDINGS / v1`

状态：`VALIDATED`，等待本轮用户决定绑定后激活。

本场景只为 `LINE-01-NAC / E-H1′ → MC-NAC-ANCHOR` 建立可判读的本地研究装置。三条
工作流并行推进：

1. 预计算 embedding manifest 与 evaluator；
2. 真实/合成 Intent—画像数据和独立标签盘点；
3. Relative Representations、vec2vec、Procrustes 与共享编码器强基线核验。

本场景不会下载五个大模型、接触真人、调用生产服务，也不会把专利原文或私密材料外发。
工具测试、合成夹具和文献复核都不能登记为 E-H1′ 已运行；它们只创造下一次真实试验能够
拒绝不公平输入的条件。

成功意味着输入哈希、五模型有序对、切片、Recall@100 分母和生命周期预算能够被机械复核。
失败或 Unknown 同样保留：现成方案完整覆盖、数据无法独立标注、模型条件不足，都会阻止
NAC 主张晋升。
