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

## 2026-07-28 — 批准 Codex v0 问题定义批次 R4 的精确 payload

<!-- research-decision:start -->
```json
{
  "decision_id": "DEC-2026-07-28-CODEX-V0-R4",
  "status": "APPROVED",
  "decided_by": "USER",
  "actions": [
    "SEND_BATCH_TO_CODEX"
  ],
  "target": {
    "id": "BATCH-20260728-V0-DEFINITION-R4",
    "version": "84955e9b34467af319bc5e5fc45cf7084375bb9b59946f46963232ab685f7eac"
  },
  "payload": {
    "destination": "OpenAI Codex",
    "classification": "NON_PUBLIC_RESEARCH",
    "total_payload_bytes": 209792,
    "disclosure_sha256": "aaf8241a5751b68df95332224dbbfa08498bded0cab799c87aa0adb8ced43d51"
  },
  "does_not_authorize": [
    "SEND_BLIND_REVIEW_TO_CLAUDE",
    "SEND_OTHER_BATCH_TO_CODEX",
    "ACTIVATE_PROBLEM_V1",
    "ACTIVATE_REAL_SCENARIO",
    "PROMOTE_STABLE_CLAIM",
    "DEPLOY_OR_PUBLISH"
  ],
  "rationale": "用户直接确认同意将该精确批次、字节数、分类和 disclosure SHA-256 对应的冻结输入发送给 OpenAI Codex。"
}
```
<!-- research-decision:end -->

本决定只授权 disclosure manifest 已冻结的 `R4` 输入。payload、目的地或指纹发生变化时
必须重新取得批准。

## 2026-07-28 — 批准 R4 匿名 Claude 盲审包

<!-- research-decision:start -->
```json
{
  "decision_id": "DEC-2026-07-28-CLAUDE-R4",
  "status": "APPROVED",
  "decided_by": "USER",
  "actions": [
    "SEND_BLIND_REVIEW_TO_CLAUDE"
  ],
  "target": {
    "id": "BATCH-20260728-V0-DEFINITION-R4",
    "version": "26590d5dca63ab062364110a01ab4b32d4d7698f85bb194533ce8a1cd80aae73"
  },
  "payload": {
    "destination": "Anthropic Claude",
    "classification": "NON_PUBLIC_DERIVED_RESEARCH",
    "payload_size_bytes": 109078,
    "payload_sha256": "26590d5dca63ab062364110a01ab4b32d4d7698f85bb194533ce8a1cd80aae73"
  },
  "does_not_authorize": [
    "ACTIVATE_PROBLEM_V1",
    "ACTIVATE_REAL_SCENARIO",
    "PROMOTE_STABLE_CLAIM",
    "CONTACT_REAL_PARTICIPANTS",
    "DEPLOY_OR_PUBLISH"
  ],
  "rationale": "用户直接确认同意将该精确匿名盲审包发送给 Anthropic Claude。"
}
```
<!-- research-decision:end -->

## 2026-07-28 — 持续授权有边界的研究模型外发

<!-- research-decision:start -->
```json
{
  "decision_id": "DEC-2026-07-28-STANDING-RESEARCH-TRANSFER",
  "status": "APPROVED",
  "decided_by": "USER",
  "actions": [
    "SEND_BATCH_TO_CODEX",
    "SEND_BLIND_REVIEW_TO_CLAUDE"
  ],
  "standing_transfer_scope": {
    "project": "research/projects/joint-action-formation",
    "action_destinations": {
      "SEND_BATCH_TO_CODEX": [
        "OpenAI Codex"
      ],
      "SEND_BLIND_REVIEW_TO_CLAUDE": [
        "Anthropic Claude"
      ]
    },
    "allowed_classifications": [
      "NON_PUBLIC_RESEARCH",
      "NON_PUBLIC_DERIVED_RESEARCH"
    ],
    "max_payload_bytes": 262144000,
    "required_exclusions_by_classification": {
      "NON_PUBLIC_RESEARCH": [
        "credentials",
        "real participant data"
      ],
      "NON_PUBLIC_DERIVED_RESEARCH": [
        "private participant data"
      ]
    },
    "requires_frozen_disclosure_manifest": true
  },
  "does_not_authorize": [
    "SEND_CREDENTIALS",
    "SEND_PRIVATE_PARTICIPANT_DATA",
    "SEND_FULL_PRIVATE_ARCHIVE",
    "CONTACT_REAL_PARTICIPANTS",
    "ACTIVATE_PROBLEM_V1",
    "ACTIVATE_REAL_SCENARIO",
    "PROMOTE_STABLE_CLAIM",
    "EXECUTE_REAL_EFFECT",
    "DEPLOY_OR_PUBLISH"
  ],
  "rationale": "用户说明以后不需要逐批取得授权；按当前上下文登记为有 disclosure、隐私排除和容量上限的研究模型外发持续授权，不扩展为现实动作或正式研究状态变更授权。"
}
```
<!-- research-decision:end -->

持续授权只消除重复询问，不降低 disclosure、哈希冻结、来源白名单、隐私排除、运行隔离和
结果晋升门槛。超出上述机器可检查范围时，系统必须阻断或另取授权。

## 2026-07-28 — 采用有界机制研究范式并登记 V2 新快照

<!-- research-decision:start -->
```json
{
  "decision_id": "DEC-2026-07-28-BOUNDED-MECHANISM-PARADIGM",
  "status": "APPROVED",
  "decided_by": "USER",
  "actions": [
    "ADOPT_BOUNDED_MECHANISM_RESEARCH_PARADIGM",
    "PRESERVE_PROBLEM_V1_SNAPSHOT",
    "REGISTER_PROBLEM_V2_AS_CANDIDATE",
    "REGISTER_SCOPED_MECHANISM",
    "CONTINUE_SCOPED_MECHANISM_RESEARCH",
    "CONTINUE_NAC_AS_SCOPED_RESEARCH"
  ],
  "target": {
    "kind": "MechanismProfile",
    "id": "MEC-NAC",
    "version": "v1",
    "path": "research/projects/joint-action-formation/mechanisms/nac.json",
    "content_sha256": "cb641a2865cd637d9101191f656049e2a4402d9b04d8f901922b3eec86ff9c72",
    "snapshot_sha256": "138b9e0609f0376d6979d9f302abe027d37fc4b00b1d9e5b49ea3064e0eb0e41"
  },
  "does_not_authorize": [
    "ACTIVATE_PROBLEM_V2",
    "SUPERSEDE_PROBLEM_V1",
    "DECLARE_NAC_VALIDATED",
    "VALIDATE_SCOPED_MECHANISM",
    "REBASE_SCOPED_MECHANISM",
    "REFUTE_SCOPED_MECHANISM",
    "SUPERSEDE_SCOPED_MECHANISM",
    "FORCE_MECHANISM_INTEGRATION",
    "ACTIVATE_REAL_SCENARIO",
    "PROMOTE_STABLE_CLAIM",
    "EXECUTE_REAL_EFFECT",
    "DEPLOY_OR_PUBLISH"
  ],
  "rationale": "用户明确要求把有界机制判断固定为长期研究范式：机制按自己的前提、问题、能力、要求、非目标和证据边界独立推进；作用域外未覆盖不构成否定，负结果只影响受检验主张，已有方案能用则复用，真实缺口才开新机制。V1 保持并存和存档，V2 只作为显化共享世界前提、服务目标、评价与研究范式的新文件；NAC 作为尚未研究到位的显式机制继续推进。"
}
```
<!-- research-decision:end -->

本决定使 `BOUNDED_MECHANISM_RESEARCH_V1` 成为后续研究的共同方法边界，并允许把 NAC
登记为 `ACTIVE_RESEARCH`。它不说明 NAC 已经有效，不允许 V2 自动激活，也不允许任何
自动结果把 V1、NAC 或其他机制标记为 superseded。

## 2026-07-28 — 按有界作用域重新登记 NAC v1

<!-- research-decision:start -->
```json
{
  "decision_id": "DEC-2026-07-28-BOUNDED-MECHANISM-PARADIGM-R2",
  "status": "APPROVED",
  "decided_by": "USER",
  "actions": [
    "REGISTER_SCOPED_MECHANISM",
    "CONTINUE_SCOPED_MECHANISM_RESEARCH",
    "CONTINUE_NAC_AS_SCOPED_RESEARCH"
  ],
  "target": {
    "kind": "MechanismProfile",
    "id": "MEC-NAC",
    "version": "v1",
    "path": "research/projects/joint-action-formation/mechanisms/nac.json",
    "content_sha256": "7f198127004e516ac882dce7507be840185f77c8f5221db5bb93a9c45d675e53",
    "snapshot_sha256": "3350482e78e343675b7780ec64462d226b4d839c7859933634a6883d46934f08"
  },
  "does_not_authorize": [
    "DECLARE_NAC_VALIDATED",
    "VALIDATE_SCOPED_MECHANISM",
    "REBASE_SCOPED_MECHANISM",
    "REFUTE_SCOPED_MECHANISM",
    "SUPERSEDE_SCOPED_MECHANISM",
    "UPDATE_SCOPED_MECHANISM_EVIDENCE",
    "FORCE_MECHANISM_INTEGRATION",
    "ACTIVATE_PROBLEM_V2",
    "ACTIVATE_REAL_SCENARIO",
    "PROMOTE_STABLE_CLAIM",
    "EXECUTE_REAL_EFFECT",
    "DEPLOY_OR_PUBLISH"
  ],
  "rationale": "用户再次明确：V1 保持存档，V2 只是新增共享知识底座；NAC 尚未研究到位，应按自身问题、前提、主张、实验和失败作用域继续作为独立研究线。此次登记吸收能力 ID、配套机制 ownership、已验证闭包与负面作用域的治理修正，不把任何未运行实验写成证成结果。"
}
```
<!-- research-decision:end -->

本决定不覆盖前一份快照，而是登记治理修正后的 NAC v1 精确内容。未来若改变主张、证据状态、
已验证范围或负面范围，仍需新的精确决定；普通研究结果只能进入候选区。
