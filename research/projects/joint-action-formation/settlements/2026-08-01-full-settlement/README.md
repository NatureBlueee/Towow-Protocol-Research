# 2026-08-01 全量研究收口入口

状态：`ACTIVE_SETTLEMENT / NO_NEW_RESEARCH_CLAIM / EXECUTION_PAUSED_FOR_ALIGNMENT`

## 为什么建立这套材料

长期研究已经产生问题重构、产品设计、局部实现、合成实验、反例、真值纠正和评价设施，但材料
分散在历史档案、V0/V1/V2、Q1--Q5、七母线 Wave 001--025、NAC 独立线和 PT-001 中。近期又
出现评测设施替代产品集成、以及把入口探针称为主线的漂移。

本目录不改写历史文件，也不把历史状态重新晋升。它只完成四件事：

1. 把原始目标、产品规划和研究阶段重新串成一条谱系；
2. 把已经得到的正结果、负结果、Unknown、未运行和失效结论分别记录；
3. 说明每类工作当时为什么值得做，以及它后来改变了什么；
4. 把主研究者原本准备做的事与纠偏后的下一步计划分开保存。

## 当前入口

- [RESEARCH-RESULTS-AND-RATIONALE.md](./RESEARCH-RESULTS-AND-RATIONALE.md)：全部研究结果的综合账本、
  研究动机、证据边界、产品意义和未完成状态。
- [ROOT-NEXT-PLAN.md](./ROOT-NEXT-PLAN.md)：主研究者独立署责的计划；包含原本准备推进的路线、
  发现的问题、纠偏后的执行顺序、停止条件和用户决定点。
- [WAVES-001-009.md](./appendices/WAVES-001-009.md)：早期七母线逐波证据附录。
- [WAVES-010-020.md](./appendices/WAVES-010-020.md)：共同 world、局部 kernel、执行、Effect、
  revoke/reopen 与 migration 逐波证据附录。
- [WAVES-021-025-AND-PT001.md](./appendices/WAVES-021-025-AND-PT001.md)：比较、公平性、假绿、
  设施漂移与 PT-001 当前状态附录。

## 当前总判断

研究已经显著推进了问题判别力和若干有界解决能力，但尚未完成原规划的产品闭环：

```text
一个可认领事项
→ 完整 RelationEpisode
→ 当前 Authority
→ 真实 ActionAttempt
→ Target Effect
→ 独立 Acceptance
→ 第二次复用与漂移重开
```

PT-001 的任务、产品行为和评价合同当前只是 `DESIGN_ONLY / NOT_YET_RUN`。在用户确认本目录中的
独立计划前，不再把它扩展成新的实验主线。

## 解释优先级

发生冲突时依次回到：

1. 根 `AGENTS.md`；
2. `research/NOW.md`；
3. Problem V2 与保留的 V1；
4. 五件激活材料及历史能力矩阵；
5. 原始实验文件和真实返回；
6. 本目录的综合解释。

本目录是导航和当前判断，不取代原始证据。
