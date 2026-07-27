# 关键研究环境决定

## 2026-07-24 — 长期实验室不绑定工具或研究轮次

v1.1 任务包作为第五阶段种子材料保留，但根研究宪章与 `research/` 服务于所有后续轮次和
相邻问题。任何 packet 都不能自动成为永久方法或身份。

## 2026-07-24 — 采用高自主、低官僚的研究环境

撤回固定 registry、统一状态枚举、强制双复核和每轮必填模板。只保留真实性、安全、工作区
保护和状态不夸大的硬边界；研究路线、工具、组织方式、证据形态和复核方式由 Agent 按问题
自主决定。

## 2026-07-27 — v1.2 完整档案成为唯一最新源包

`Towow_Complete_Research_Archive_v1.2_2026-07-27/` 是当前材料环境的唯一最新归档来源。
旧 seed packet、历史 ZIP、论文和 release 继续作为证据保留，但不单独声明当前状态。

## 2026-07-27 — 原始档案与工作视图分层

原始包保持不变。分类、拆分、文本提取、时间线和全局理解放在
`research/projects/a2a-reconstruction/`，并保留源路径、SHA-256、ZIP 成员路径和源行号。
不通过移动原件或覆盖旧版本制造表面整洁。

## 2026-07-27 — 统一接口而不熔平历史研究核

材料整理不预设六个 canonical roots 或任何单一长文已经无损吸收 NAC、BIC、SJAC、JAA、
PFE、CRA、Harness、Compiled World 等独立体系。当前先分别记录它们解决的缺口、原生能力、
证据和后续身份；是否合并由后续研究判断。

## 2026-07-27 — 能力保真而不是名称映射

历史设计是否保留，以原系统还能否完成原来的工作判断，不以旧术语能否映射到六个 canonical
roots 判断。每项保留判断必须包含正例、移除关键决定后重新出现的失败、原始来源、当前 owner
和人工重建状态。

当前审计入口是 `research/projects/a2a-reconstruction/04_audit/README.md`。

## 2026-07-27 — 六 roots 只承担关系运行时正式事实

Entity、Mandate、RelationVersion、Assertion、Commitment、Operation 继续作为关系运行时
的最小事实范围。它们不替代 Discovery provider、Boundary Oracle、Relation constitution、
Formation planner、Capability assurance 或 Harness 的 Problem/Design/Engineering IR。

跨内核只统一身份引用、版本、事件、证据、来源和依赖。

## 2026-07-28 — 采用有界高自治、按需批次和分级晋升

<!-- research-decision:start -->
```json
{
  "decision_id": "DEC-2026-07-28-ENVIRONMENT-V1",
  "status": "APPROVED",
  "decided_by": "USER",
  "actions": [
    "IMPLEMENT_RESEARCH_ENVIRONMENT",
    "REGISTER_PROBLEM_V0_AS_SEED",
    "ACTIVATE_SEVEN_NATIVE_DEFINITION_LINES",
    "AUTO_VALIDATE_ARCHIVE_SYNTHETIC_LOCAL_SCENARIOS",
    "RUN_ON_DEMAND_BATCHES",
    "USE_CODEX_PRIMARY_CLAUDE_BLIND_REVIEW"
  ],
  "does_not_authorize": [
    "ACTIVATE_PROBLEM_V1",
    "ACTIVATE_REAL_SCENARIO",
    "PROMOTE_STABLE_CLAIM",
    "CONTACT_REAL_PARTICIPANTS",
    "SEND_BATCH_TO_CODEX",
    "SEND_BLIND_REVIEW_TO_CLAUDE",
    "SEND_PRIVATE_ARCHIVE_TO_EXTERNAL_REVIEWER",
    "DEPLOY_OR_PUBLISH"
  ],
  "rationale": "允许 Agent 在冻结的问题与场景边界内自主提出子问题和候选结果，但让核心问题、现实场景、稳定主张和现实行动继续由用户决定。"
}
```
<!-- research-decision:end -->

当前长问题登记为 `Problem v0 / SEED`。第一批恢复全部七条原生研究线，而不是先压缩成少数
统一机制。Codex 在本地来源白名单上运行；Claude 只接收隔离、最小且不包含预期答案的盲审
材料。自动结果最高只能进入候选区。

## 2026-07-28 — 原始档案使用哈希指针，运行区有硬预算

v1.2 原始档案继续留在当前只读共享目录，不复制进 Git 或每条研究线的 worktree。Git 跟踪
`research/sources/archive-v1.2.json` 中的 manifest 指针、治理工具、研究契约、候选返回和
正式成果。

`.research-runtime/` 每批上限 250 MiB、总上限 2 GiB。达到上限时拒绝新运行，不自动删除
历史证据。
