# 审计后的研究排序

本文件只登记审计完成后允许进入的判别研究。它不表示实验已经开始。

## 共同开工条件

任何新实验必须在开工前写清：

1. 卡住的设计决策；
2. 至少一个会改变设计的反向结果；
3. 最便宜的判别方式；
4. 成功、失败和不确定分别怎样修改系统；
5. 数据、权限、成本和停止条件。

答不出这些问题的工作归入：

```text
CI_REGRESSION
IMPLEMENTATION_ASSURANCE
ARCHIVAL_CALIBRATION
INSTRUMENTATION
```

而不是研究实验。

## Q1：公平强中心 Agent 基线

- 卡住：先建设中心权威语义层，还是立即建设联邦层。
- 最便宜判别：在 R5.4/R5C 同输入、同模型、同工具、同查询预算和同 Effect Gate 下运行
  transport-safe 强中心 Agent。
- 反向结果：中心 Agent 保持私域、拒绝权、责任和 Acceptance Gate 仍打平联邦。
- 成功：若中心失败且只能通过复制私域或冒领权威补足，联邦层获得结构支持。
- 失败：若中心打平，联邦改为条件插件，产品先交付 Mandate/Effect/Acceptance 语义。
- 不确定：transport 或工具失败不计架构结果，修复测量后重跑。
- 关联：CAP-RUN-007、CLM-015、CLM-022。

## Q4：从未经编码材料推断 Router 判据

- 卡住：Router 是自动组件、风险扫描器还是人机 checklist。
- 最便宜判别：对公开真实材料盲化输入，不提供研究者 truth fields，独立填制度充分性、
  信息可集中性、可信 Hub、Authority、Standing、witness、Acceptance 和机制组合。
- 反向结果：对关键字段一致性低，或错误集中在会造成 false collapse 的字段。
- 成功：高一致性可逐步自动化。
- 失败：低一致性则只保留 checklist；高召回低精度则只做 probe ranking。
- 不确定：材料缺失与模型误判必须分开。
- 关联：CAP-REL-001、CAP-RUN-006、CLM-020。

## Q2：三名 OPC 的 Mandate explain-back

- 卡住：Mandate 应显式暴露给用户，还是内部推断后渐进确认。
- 最便宜判别：3 名真实 OPC、每人 1–2 个真实事项、结构化卡片与自然语言摘要对照。
- 反向结果：关键边界 explain-back 错误、修订负担高于人类中介或拒绝维护版本。
- 成功：用户可编辑 Mandate 工作台。
- 失败：Mandate 保留内部对象，只在高风险 Effect Gate 确认差异。
- 不确定：样本只用于产品形态判别，不外推总体频率。
- 关联：CAP-AUTH-002、CLM-019。

## Q3：单案 Q4 causal formation

- 卡住：PFE/formation planner 是核心引擎还是过程记录。
- 最便宜判别：一个低风险、可撤销、7–14 天的真实事项；冻结前态；一个主要 operator；
  一名独立裁决者；一个目标世界 Effect。
- 反向结果：强基线得到相同路径，或移除 operator 后路径仍成立。
- 成功：路径前态不存在、operator 后出现、消融失败、Authority 认领并达到 Q4 Effect。
- 失败：降级为 discovery、clarification 或 harmful overhead。
- 不确定：没有目标 witness 或前态未冻结，不得宣称 formation。
- 关联：CAP-FORM-002、CLM-005、CLM-013。

## Q5：真实编译复用

- 前置条件：Q3 至少一条真实 formation 成立。
- 卡住：Formation Compiler 是长期价值来源还是额外治理负担。
- 判别：同一关系第二次运行，再加入一次 material drift。
- 反向结果：高认知时间、披露、错误或后悔没有下降，或 scoped reopen 漏开关键依赖。
- 成功：复用成本下降且 Authority、Effect、退出和 Acceptance 不退化。
- 失败：编译仅用于高风险或高频稳定局部。
- 关联：CAP-RUN-003、CAP-RUN-004、CLM-016、CLM-017。

## 暂停项

在上述问题得到结果前，不新增：

- 大规模合成生成器；
- 本体自评分；
- materiality 同源真值实验；
- 漂移大样本模拟；
- 不直接卡住设计决策的命题或术语；
- 完整五阶段真人研究。

