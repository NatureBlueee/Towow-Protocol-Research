# 交互与矫正材料视图

## 1. 三类材料不能混用

### 原始可取得交互

位置：

```text
Towow_Complete_Research_Archive_v1.2_2026-07-27/
01_INTERACTIONS_AND_CORRECTIONS/01_RAW_CHAT_EXPORT/
```

作用：保留当前包中实际取得的对话文本。  
边界：它不是平台后台逐消息、逐时间戳的完整数据库导出。

### 重建纪事与矫正账本

位置：

```text
Towow_Complete_Research_Archive_v1.2_2026-07-27/
01_INTERACTIONS_AND_CORRECTIONS/00_INTERACTION_CORRECTION_CHRONICLE.md
Towow_Complete_Research_Archive_v1.2_2026-07-27/
01_INTERACTIONS_AND_CORRECTIONS/03_CORRECTION_LEDGER.csv
```

作用：把散落在对话和阶段产物中的方向变化组织成可检索历史。  
边界：这是重建材料，不应冒充原始逐轮记录。

### 审稿与研究重置

位置：

```text
Towow_Complete_Research_Archive_v1.2_2026-07-27/
01_INTERACTIONS_AND_CORRECTIONS/04_REVIEWER_FEEDBACK_FULL.md
Towow_Complete_Research_Archive_v1.2_2026-07-27/
01_INTERACTIONS_AND_CORRECTIONS/06_REVIEW_TO_V1_2_DECISION_PROGRAM.md
Towow_Complete_Research_Archive_v1.2_2026-07-27/
10_CURRENT_DECISION_PROGRAM/
```

作用：解释为什么 v1.2 将研究从合成确认转向决策判别。  
边界：评审意见是研究输入，不是对历史成果的最终裁决。

## 2. 查询顺序

若要回答“某次矫正为什么发生”，采用以下顺序：

1. 在 `03_CORRECTION_LEDGER.csv` 定位轮次和纠正主题；
2. 回到原始可取得交互核对用户原话；
3. 查当时阶段产物，确认纠正前的真实设计；
4. 查纠正后的版本，判断修改是否真的落地；
5. 将“用户要求变化”和“证据迫使变化”分开记录。

## 3. 当前已确认的过程性漂移

- 多套独立理论被过早压入统一最小本体，原生解题能力没有先做保真检查；
- 形式化和合成实验的叙事重量一度超过了真实系统证据；
- 研究包持续增长，但仓库动态入口仍停在较早的 R5 状态；
- “正式论文”一度同时承担研究基座、协议、实验报告和预注册，导致用途混淆。

更完整的证据与边界见：

- [漂移与转折点](../00_orientation/DRIFT_AND_TURNING_POINTS.md)
- [研究进程时间线](../00_orientation/RESEARCH_TIMELINE.md)
- [证据与主张状态](../00_orientation/EVIDENCE_AND_CLAIM_STATUS.md)
