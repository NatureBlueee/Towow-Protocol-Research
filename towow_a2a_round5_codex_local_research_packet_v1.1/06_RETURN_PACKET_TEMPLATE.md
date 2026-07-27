# 第五阶段本地实验室返回包模板

## 1. 返回包目标

返回包必须让首席研究者在不依赖口头转述、不重新登录本地环境的情况下：

- 复核真实发生了什么；
- 重跑关键结果；
- 判断哪些结论影响理论；
- 查看代码和工作区如何变化；
- 理解失败、成本和边界；
- 决定下一轮研究。

返回包不是产品演示包，也不是只报告成功的周报。

---

## 2. 最低目录结构

```text
return-packet/
  RETURN_SUMMARY.md
  ENVIRONMENT_FACTS.json
  RESEARCH_STATE.yaml
  DECISION_LOG.md
  CLAIM_EVIDENCE_UPDATE.csv
  NEXT_RESEARCH_ACTIONS.md
  git/
    baseline.txt
    final.txt
    status.txt
    commits.txt
    changes.patch
  experiments/
    <run_id>/...
  code_changes/
    FILE_MAP.md
    TEST_RESULTS.md
    ROLLBACK.md
  independent_reviews/
  failures/
  blockers/
  manifests/
    MANIFEST.json
    CHECKSUMS.sha256
```

若某目录无内容，保留一个 `NONE.md` 说明为什么为空。

---

## 3. `RETURN_SUMMARY.md` 模板

```markdown
# 通爻 A2A 第五阶段本地实验室返回摘要

## 1. 最出乎预期的发现
- 先写最可能改变理论或工程方向的结果，不按完成顺序写。

## 2. 真实环境中发生了什么
- 工作区、任务、Agent、模型、工具、权限和外部效果。
- 哪些是现实任务，哪些仍然是受控实验。

## 3. 当前主张变化
| claim_id | 原状态 | 新状态 | 变化原因 | 证据路径 | 设计后果 |

## 4. 哪些结构产生了真实增量
- 判别力、生成力和兑现能力分别说明。
- 与人工、静态、中心化和现有 Harness 基线比较。

## 5. 哪些结构没有价值或应该被合并/降级
- 删除它会失去什么；保留它的成本是什么。

## 6. 能力形成证据
- 形成条件、干预、Witness、留出、认领和实际效果。
- 哪些只是语言重述或目标降级。

## 7. 主权 A2A 真实性
- 边界如何实施；协调器能否绕过；拒绝/退出是否真实；成本是多少。

## 8. 目标与价值保真
- 原目标、修订目标、保留/放弃价值和残余缺口。

## 9. 成本和 break-even
- token、墙钟、人类介入、等待、披露、返工、恢复和基线。
- 中心化方案更好的情况必须写明。

## 10. 独立验证与分歧
- 独立实现/评审如何隔离；发现了什么；仍有哪些分歧。

## 11. 失败、异常和未解决问题
- 每项为什么失败；是理论、实现、配置还是环境问题。
- 下一项建设性行动。

## 12. 实际代码变化
- baseline/final commit、主要 diff、测试、回滚和未提交文件。

## 13. 无法调用的资源
- 具体工具、错误、最小缺失条件和已准备的可执行接口。

## 14. 下一步最有价值的研究行动
- 只列会显著改变判断或新增能力的行动，说明优先级理由。

## 15. 证据索引
- 每个重大结论对应文件和可复现命令。
```

---

## 4. `ENVIRONMENT_FACTS.json`

必须来自实际工具和文件，不得凭记忆填写。至少包括：

- workspace、repo root、OS；
- Git baseline/final；
- dirty/untracked；
- AGENTS 文件；
- 当前 Codex Agent、模型、CLI/App、其他模型/SDK 版本；
- 测试入口；
- 直接本地执行 smoke、实际命令和结果文件证据；
- 允许和禁止路径；
- 外部效果入口；
- 未成功资源和错误。

---

## 5. `RESEARCH_STATE.yaml`

使用任务包模板，保留最终：

- 当前最承重问题；
- 活跃假设；
- 已知事实；
- 已否定解释；
- 当前证据等级；
- 最近方向改变及触发证据；
- 下一候选实验；
- 阻塞和所需授权。

---

## 6. `DECISION_LOG.md`

按时间记录所有重要方向改变：

- 原计划；
- 新证据；
- 为什么改变；
- 哪些工作停止、合并或新增；
- 如何避免事后重写历史。

---

## 7. `CLAIM_EVIDENCE_UPDATE.csv`

字段至少包括：

```text
claim_id,claim,previous_status,new_status,evidence_grade,scope,
evidence_paths,counterevidence,alternative_explanations,
design_consequence,next_discriminating_action
```

必须包含被削弱、推翻和仍未知的主张。

---

## 8. 实验目录

每个关键 run 遵守 `04_EVIDENCE_CONTRACT.md`。至少保留：

- 输入、配置、提示；
- 模型/Agent 调用；
- 事件和边界轨迹；
- stdout/stderr/exit code；
- token、成本、时间和人类介入；
- 原始和修订目标；
- 失败与恢复；
- 结果分析；
- 单命令复现；
- checksums。

---

## 9. 代码变化

`FILE_MAP.md` 应把理论对象映射到真实代码：

```text
理论/语义对象 → 文件/类型/函数 → 状态转换 → 测试 → 证据等级
```

`TEST_RESULTS.md` 包含所有通过、失败、跳过和不稳定测试。不要只写“全部通过”。

`ROLLBACK.md` 提供删除 worktree、revert commit、停止服务和清理临时资源的命令。

---

## 10. 独立评审

每份评审包括：

- 评审任务；
- 评审者可见/不可见材料；
- 模型/Agent/实现版本；
- 输出、反例和代码；
- 与主研究分歧；
- 研究者如何处理分歧。

若没有真正独立评审，明确说明，不要用自评替代。

---

## 11. 失败和阻塞

`failures/` 保存失败实验、中心化更优、无价值机制、无法复现和事故。

`blockers/` 只用于确实需要外部条件的事项。每项说明：

- 缺少什么；
- 为什么当前方法不能绕过；
- 最小授权/凭据；
- 风险；
- 获得后可以直接运行的命令或任务；
- 不提供时当前最好近似方案。

---

## 12. `NEXT_RESEARCH_ACTIONS.md`

不要列大而全路线图。按优先级给出 1–5 项：

- 哪个关键不确定性；
- 为什么最承重；
- 什么实验最有区分力；
- 需要什么外部条件；
- 可能支持/推翻什么；
- 会改变什么设计或能力。

---

## 13. Manifest 与校验

`MANIFEST.json` 列出：

- 返回包版本；
- baseline/final commit；
- 文件路径、作用和 SHA-256；
- 实验 run_id；
- 模型/Agent 调用索引；
- 环境和时间范围；
- 是否包含秘密或受限数据（正常应为 false）。

`CHECKSUMS.sha256` 覆盖所有返回文件。

---

## 14. 返回时的会话消息

会话中只需给出：

1. 返回包绝对路径与 zip 路径；
2. Git baseline/final/dirty；
3. 3–7 条最重要发现；
4. 关键证据路径；
5. 真实阻塞；
6. 下一步最高价值行动。

完整分析必须在返回包中，不能只存在会话消息里。
