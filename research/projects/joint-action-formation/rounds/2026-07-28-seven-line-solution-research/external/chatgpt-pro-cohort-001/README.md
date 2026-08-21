# ChatGPT Pro cohort 001

## 状态与证据边界

- Cohort：`chatgpt-pro-cohort-001`
- 母线：G1–G7，各自使用独立会话上下文
- 当前状态：`SEVEN_OF_SEVEN_RETURNED / SEVEN_OF_SEVEN_AUDITED`
- 用途：产生外部模型的候选解释、候选解法、反例与下一步实验建议
- 证据资格：`EXTERNAL_MODEL_CANDIDATE_EVIDENCE_ONLY`
- 不构成：工作区正式事实、机制有效性证据、任务完成证据或用户批准
- 本文件不记录、概括或评价任何返回内容

## 统一去偏置规则

1. 每个会话只收到该母线的原问题、作用域和要求，不带入本地当前预期答案或希望得到的结论。
2. 不以证明通爻独占、原创或必须新增机制为目标。
3. 强中心、成熟技术、人工制度、现有协议、adapter 或它们的组合若完整解决原问题，均视为成功。
4. 要求分别给出：问题重建、最强现有方案或组合、必要前提、失败边界、仍存 residual，以及最有区分力的下一项本地检验。
5. 不把会话分离、模型共识或表达完整视为独立证据；返回仍需由本地材料、实现、实验和审计复核。

## 会话登记

| 母线 | Bounded question | 会话 | 状态 |
|---|---|---|---|
| G1 `DISCOVERY-BEFORE-SEARCH` | 在动态、未声明且局部私有的环境中，怎样让潜在互补关系获得足够可见性，同时保持最低披露、拒绝保真与可发现性边界；强中心、成熟技术或组合能否完整解决，若不能，精确 residual 是什么？ | [Pro G1](https://chatgpt.com/c/6a69e0b7-64ac-83ea-9958-f197cf0cde32) / [本地转写](./G1-return.md) / [独立审计](./G1-AUDIT.md) | `RETURN_RECEIVED / REVISE_BEFORE_EXPERIMENT` |
| G2 `RELATION-FROM-TASK` | 当参与者、角色、动作、证据、用途、退出和评价规则未预先给定时，怎样形成可共同修改、保留异议、可版本化并可进入求解与执行的关系表示；现有方案或组合能否完整解决，若不能，精确 residual 是什么？ | [Pro G2](https://chatgpt.com/c/6a69e1d0-8bb0-83ea-94a6-294366409611) / [本地转写](./G2-return.md) / [独立审计](./G2-AUDIT.md) | `RETURN_RECEIVED / REVISE_BEFORE_EXPERIMENT` |
| G3 `FORM-REACHABILITY` | 当当前任务不可达时，怎样正确诊断原因并选择 ask、search、probe、tool、partner、authority、task representation 或 exit，使其变为可达或产生可行动的不可达解释；现有方案或组合能否完整解决，若不能，精确 residual 是什么？ | [Pro G3](https://chatgpt.com/c/6a69e303-7cb4-83ea-b3ba-47b1a969dd66) / [本地转写](./G3-return.md) / [独立审计](./G3-AUDIT.md) | `RETURN_RECEIVED / REVISE_BEFORE_EXPERIMENT` |
| G4 `CAPABILITY-TO-RELIANCE` | 怎样预测具体 operation 在给定 executor、environment、version、permission、resource 与 recovery 条件下能否首次完成，并在组合、漂移和恢复中保持可依赖；成熟组合或强中心能否完整解决，若不能，精确 residual 是什么？ | [Pro G4](https://chatgpt.com/c/6a69e1d0-dadc-83ea-a0db-28f41051b572) / [本地转写](./G4-return.md) / [独立审计](./G4-AUDIT.md) | `RETURN_RECEIVED / REVISE_BEFORE_EXPERIMENT` |
| G5 `AUTHORITY-COMPOSITION` | 怎样在真实状态推进中完整区分并组合 identity、capability、Principal/AuthorityLocus、Mandate、versioned stance、Commitment、Reservation 与 Standing，避免它们之间的错误蕴含；成熟栈或组合能否完整解决，若不能，精确 residual 是什么？ | [Pro G5](https://chatgpt.com/c/6a69e303-9b54-83ea-8772-9aadc3ec9377) / [本地转写](./G5-return.md) / [独立审计](./G5-AUDIT.md) | `RETURN_RECEIVED / REVISE_BEFORE_EXPERIMENT` |
| G6 `EFFECT-THAT-COUNTS` | 怎样使 ActionAttempt、Effect、Adoption、Acceptance 与 Settlement 在不同 authority domain 下分别成立或失败且可重建，不发生误晋升；现有 transaction、event、workflow、readback 与人工验收组合能否完整解决，若不能，精确 residual 是什么？ | [Pro G6](https://chatgpt.com/c/6a69e303-a104-83ea-85e3-9e2c29220908) / [本地转写](./G6-return.md) / [独立审计](./G6-AUDIT.md) | `RETURN_RECEIVED / REVISE_BEFORE_EXPERIMENT` |
| G7 `REUSE-AND-SAFE-REOPEN` | 怎样把前六线的解变成可恢复运行能力，在依赖或 Defeater 漂移时正确继续、阻断、恢复或局部重开，并保持 Context 充分与历史可迁移；成熟 workflow、人工 amendment 或组合能否完整解决，若不能，精确 residual 是什么？ | [Pro G7](https://chatgpt.com/c/6a69e1d0-d564-83ea-9628-8964278ae7be) / [本地转写](./G7-return.md) / [独立审计](./G7-AUDIT.md) | `RETURN_RECEIVED / REVISE_BEFORE_EXPERIMENT` |
