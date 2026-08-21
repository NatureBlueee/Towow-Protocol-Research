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

## 2026-07-28 — 激活 Problem v2

<!-- research-decision:start -->
```json
{
  "decision_id": "DEC-2026-07-28-ACTIVATE-PROBLEM-V2",
  "status": "APPROVED",
  "decided_by": "USER",
  "actions": [
    "ACTIVATE_PROBLEM"
  ],
  "target": {
    "kind": "ProblemContract",
    "id": "PRB-JOINT-ACTION-FORMATION",
    "version": "v2",
    "source_path": "research/projects/joint-action-formation/problem/v2-candidate.json",
    "source_sha256": "c8d60f43508e2f375cedc7f9db7c6949341a80562d9edb9973910c3a33a54da1",
    "activation_bundle_path": "research/projects/joint-action-formation/problem/activation/v2.json",
    "activation_bundle_sha256": "e24b7e7638de0de7f8a835798bbd60b3cad5f79d157359b1a827e938bd99b421"
  },
  "does_not_authorize": [
    "SUPERSEDE_PROBLEM_V1",
    "ACTIVATE_RESEARCH_LINE",
    "ACTIVATE_SCENARIO",
    "ACTIVATE_REAL_SCENARIO",
    "VALIDATE_SCOPED_MECHANISM",
    "REBASE_SCOPED_MECHANISM",
    "REFUTE_SCOPED_MECHANISM",
    "SUPERSEDE_SCOPED_MECHANISM",
    "PROMOTE_STABLE_CLAIM",
    "EXECUTE_REAL_EFFECT",
    "DEPLOY_OR_PUBLISH"
  ],
  "rationale": "用户在明确区分当前任务负责 V2 激活、后续新任务负责独立研究线，并确认激活不会自动启动 NAC、场景或实验后，回复“好的，去吧”，明确授权按当前候选与五件材料闭包的精确 SHA-256 激活 Problem v2。"
}
```
<!-- research-decision:end -->

本决定只改变 `PRB-JOINT-ACTION-FORMATION / v2` 的正式问题状态。V1 继续作为不可覆写的
历史候选快照保留；NAC 研究线仍为 `DRAFT`，没有机制场景、现实 Effect、稳定主张或部署被
同时授权。

## 2026-07-28 — 立即激活 NAC E-H1′ 研究线

<!-- research-decision:start -->
```json
{
  "decision_id": "DEC-2026-07-28-ACTIVATE-NAC-H1-LINE",
  "status": "APPROVED",
  "decided_by": "USER",
  "actions": [
    "ACTIVATE_RESEARCH_LINE"
  ],
  "target": {
    "kind": "LineContract",
    "id": "LINE-01-NAC",
    "version": "v1",
    "source_path": "research/projects/joint-action-formation/lines/01-nac.json",
    "source_sha256": "f74001c4a58dda86efe3b720422199cc9f054a504bbc35f52b07f8e4ed586d0a"
  },
  "does_not_authorize": [
    "VALIDATE_SCOPED_MECHANISM",
    "REBASE_SCOPED_MECHANISM",
    "REFUTE_SCOPED_MECHANISM",
    "SUPERSEDE_SCOPED_MECHANISM",
    "UPDATE_SCOPED_MECHANISM_EVIDENCE",
    "ACTIVATE_REAL_SCENARIO",
    "CONTACT_REAL_PARTICIPANTS",
    "EXECUTE_REAL_EFFECT",
    "DEPLOY_OR_PUBLISH"
  ],
  "rationale": "用户发现上一轮实际活跃研究线为 0 后明确纠正：现在应该启动，并要求多条工作流同时开启研究。按当前唯一具备 V2 LineContract、机制 profile、scoped claim、历史失败门和已解决现成方案检查的 LINE-01-NAC 精确快照，登记为 ACTIVE；激活后的同轮一手来源复核已把 vec2vec 的公平条件从错误的 same-K 修正为原生信息条件加完整资源账。只启动 E-H1′ → MC-NAC-ANCHOR，不顺带激活 H2–H8 或其他母线。"
}
```
<!-- research-decision:end -->

这项决定把 `LINE-01-NAC / v1` 从研究准备状态迁入正式研究执行状态。激活只表示允许开始
构造输入、基线、反例和实验；它不改变 `MEC-NAC` 的证据状态，也不把工具、合成夹具或
并行 Agent 数量计为机制证据。

## 2026-07-28 — 激活 NAC E-H1′ 本地判别沙箱

<!-- research-decision:start -->
```json
{
  "decision_id": "DEC-2026-07-28-ACTIVATE-NAC-H1-SCENARIO",
  "status": "APPROVED",
  "decided_by": "USER",
  "actions": [
    "ACTIVATE_SCENARIO"
  ],
  "target": {
    "kind": "ScenarioContract",
    "id": "SCN-NAC-H1-PRECOMPUTED-EMBEDDINGS",
    "version": "v1",
    "source_path": "research/projects/joint-action-formation/scenarios/nac-h1-precomputed-embeddings-v1.json",
    "source_sha256": "1ecff6d315d64d668b987c3b0c177e1ecb1c5779c97bba982242d0917fc82440"
  },
  "does_not_authorize": [
    "ACTIVATE_REAL_SCENARIO",
    "CONTACT_REAL_PARTICIPANTS",
    "SEND_PRIVATE_PARTICIPANT_DATA",
    "SEND_PATENT_DISCLOSURE_TEXT",
    "CREATE_PAID_RESOURCES",
    "VALIDATE_SCOPED_MECHANISM",
    "PROMOTE_STABLE_CLAIM",
    "EXECUTE_REAL_EFFECT",
    "DEPLOY_OR_PUBLISH"
  ],
  "rationale": "用户要求现在就实际启动，并要求多条线同时研究。本决定只激活本地可逆的 E-H1′ 机制沙箱：并行推进预计算 embedding evaluator、数据/标签盘点和公开强基线复核；不接触真人、生产或付费资源，不把工具测试和文献判断写成机制结果。"
}
```
<!-- research-decision:end -->

本场景是 `LOCAL_SANDBOX / MECHANISM`，而非真人或生产场景。真实五模型运行、外部私密材料、
现实 Effect 和任何主张晋升仍需要各自满足输入、披露、证据和用户决定边界。

## 2026-07-28 — 以原生信息条件修正 NAC E-H1′ 沙箱

<!-- research-decision:start -->
```json
{
  "decision_id": "DEC-2026-07-28-ACTIVATE-NAC-H1-SCENARIO-V1-1",
  "status": "APPROVED",
  "decided_by": "USER",
  "actions": [
    "ACTIVATE_SCENARIO"
  ],
  "target": {
    "kind": "ScenarioContract",
    "id": "SCN-NAC-H1-PRECOMPUTED-EMBEDDINGS",
    "version": "v1.1",
    "source_path": "research/projects/joint-action-formation/scenarios/nac-h1-precomputed-embeddings-v1.1.json",
    "source_sha256": "879ed1b85adc2b706e109551ca8856f567b32aa168d50ef4019f566a472ee861"
  },
  "does_not_authorize": [
    "ACTIVATE_REAL_SCENARIO",
    "CONTACT_REAL_PARTICIPANTS",
    "SEND_PRIVATE_PARTICIPANT_DATA",
    "SEND_PATENT_DISCLOSURE_TEXT",
    "CREATE_PAID_RESOURCES",
    "VALIDATE_SCOPED_MECHANISM",
    "PROMOTE_STABLE_CLAIM",
    "EXECUTE_REAL_EFFECT",
    "DEPLOY_OR_PUBLISH"
  ],
  "rationale": "用户明确要求现在启动并让多条工作流同时研究。启动后的一手来源复核发现 v1 错误要求 vec2vec 与 NAC 使用相同 shared semantic samples；本决定在相同本地、可逆、非现实授权范围内激活修正版 v1.1，让各方案使用原生信息条件并统一核算完整资源。v1 保留为未实际开 batch 的历史快照，不被悄悄改写。"
}
```
<!-- research-decision:end -->

v1.1 是当前执行场景。它只修正实验公平性，不扩大参与者、数据、网络、生产或机制结论权限。

## 2026-07-28 — 允许向第三方研究服务发送内部概念与问题框架

<!-- research-decision:start -->
```json
{
  "decision_id": "DEC-2026-07-28-ALLOW-THIRD-PARTY-RESEARCH-QUERY",
  "status": "APPROVED",
  "decided_by": "USER",
  "actions": [
    "SEND_RESEARCH_QUERY_TO_THIRD_PARTY"
  ],
  "target": {
    "kind": "DisclosureClass",
    "id": "TOWOW-INTERNAL-RESEARCH-CONCEPTS",
    "version": "v1",
    "allowed_content": [
      "通爻内部研究概念名称",
      "有界问题框架",
      "待核验机制描述",
      "用于查找公开一手方案的反例与比较问题"
    ]
  },
  "does_not_authorize": [
    "SEND_CREDENTIALS",
    "SEND_PRIVATE_PARTICIPANT_DATA",
    "SEND_PATENT_DISCLOSURE_TEXT",
    "SEND_COMPLETE_PRIVATE_ARCHIVE",
    "CONTACT_REAL_PARTICIPANTS",
    "EXECUTE_REAL_EFFECT",
    "DEPLOY_OR_PUBLISH"
  ],
  "rationale": "在第三方研究检索因内部 Boundary Oracle/BIC 概念与问题框架被披露保护拦截后，用户明确回复“我觉得完全可以发送给第三方的”。本决定允许为了公开一手来源核验发送该类研究查询，但不扩大到凭据、真人私密数据、专利原文、完整私有档案或现实动作。"
}
```
<!-- research-decision:end -->

本轮随后尝试恢复 AgentKey 查询，但服务返回月度额度已耗尽，未取得外部研究结果。这个基础
设施失败不构成现成方案不存在的证据；相关外部核验保持待补。

## 2026-07-28 — 激活七母线的九条 V2 有界研究线

<!-- research-decision:start -->
```json
{
  "decision_id": "DEC-2026-07-28-ACTIVATE-FULL-LINE-RESEARCH",
  "status": "APPROVED",
  "decided_by": "USER",
  "actions": [
    "ACTIVATE_RESEARCH_LINES"
  ],
  "target": {
    "kind": "LineActivationBundle",
    "id": "FULL-LINE-V2-STARTUP",
    "version": "v1",
    "lines": [
      {
        "id": "LINE-01-BOUNDARY-SUFFICIENCY-V2",
        "path": "research/projects/joint-action-formation/lines/01-boundary-sufficiency-v2.json",
        "sha256": "d6b27e662d16833e28cb93bafb74a9417737e183e0512fcaf3bc01b090a24a42"
      },
      {
        "id": "LINE-02-RELATION-MATERIALITY-V2",
        "path": "research/projects/joint-action-formation/lines/02-relation-materiality-v2.json",
        "sha256": "7b6d3a165d51acbeb8abb162ee096c995187e08780d077e7fd20a9a76da23944"
      },
      {
        "id": "LINE-02-PRIVATE-COLUMN-V2",
        "path": "research/projects/joint-action-formation/lines/02-private-column-v2.json",
        "sha256": "566fda9f389568f2f923296132ea5248b3196680ccc8290a5bb506a1202a6570"
      },
      {
        "id": "LINE-03-CONDITION-FORMATION-V2",
        "path": "research/projects/joint-action-formation/lines/03-condition-formation-v2.json",
        "sha256": "b3abef4554816186a9b320e6f82b6bdb1c1303176d727b00308c51e7f63d9267"
      },
      {
        "id": "LINE-03-TYPED-UNKNOWN-V2",
        "path": "research/projects/joint-action-formation/lines/03-typed-unknown-v2.json",
        "sha256": "60e1ec792a7097d637e24aef289ed8ad52308c967a34aacab2260ce606197fcf"
      },
      {
        "id": "LINE-04-CAPABILITY-REALIZATION-V2",
        "path": "research/projects/joint-action-formation/lines/04-capability-realization-v2.json",
        "sha256": "f8f30b7c060f7cac6abadc2674092b29024287d04730ab74b9aad3eae9cdb123"
      },
      {
        "id": "LINE-05-AUTHORITY-ADAPTER-V2",
        "path": "research/projects/joint-action-formation/lines/05-authority-adapter-v2.json",
        "sha256": "04ecd72b5b1b2fb6a4a50060b16de789ca47cfcec81860da12a67d94d27de42d"
      },
      {
        "id": "LINE-06-EFFECT-AUTHORITY-GATE-V2",
        "path": "research/projects/joint-action-formation/lines/06-effect-authority-gate-v2.json",
        "sha256": "dbcd5f05b3f716c8483d2d18fa6854e6d0ea5643bd8ea0a15fbd280b64c58e4b"
      },
      {
        "id": "LINE-07-SCOPED-REOPEN-V2",
        "path": "research/projects/joint-action-formation/lines/07-scoped-reopen-v2.json",
        "sha256": "756dc4cef4373ee8f2859805ca83d583c555e1bf10a3576ef062886b11a72345"
      }
    ]
  },
  "does_not_authorize": [
    "REGISTER_SCOPED_MECHANISM",
    "VALIDATE_SCOPED_MECHANISM",
    "REBASE_SCOPED_MECHANISM",
    "REFUTE_SCOPED_MECHANISM",
    "PROMOTE_STABLE_CLAIM",
    "ACTIVATE_REAL_SCENARIO",
    "CONTACT_REAL_PARTICIPANTS",
    "EXECUTE_REAL_EFFECT",
    "DEPLOY_OR_PUBLISH"
  ],
  "rationale": "用户明确给自己设立持续 Goal“全线研究启动”。七母线启动审计与一手强基线复核已经完成，并把异质能力拆成九条与 Problem v2 精确绑定的 scoped LineContract。激活只允许本地可逆的理论、来源、数据、合成反例和工程门禁研究；真人、现实、生产和正式机制状态仍各自受限。"
}
```
<!-- research-decision:end -->

本决定与已激活的 `LINE-01-NAC` 合并后，使 Problem v2 拥有十条正式 ACTIVE scoped lines。
它不迁移 v0 的七条历史 `ACTIVE` 标签，也不把九条线注册成九个新机制。

## 2026-07-28 — 激活全线本地研究沙箱

<!-- research-decision:start -->
```json
{
  "decision_id": "DEC-2026-07-28-ACTIVATE-FULL-LINE-SCENARIO",
  "status": "APPROVED",
  "decided_by": "USER",
  "actions": [
    "ACTIVATE_SCENARIO"
  ],
  "target": {
    "kind": "ScenarioContract",
    "id": "SCN-FULL-LINE-LOCAL-STARTUP",
    "version": "v1",
    "source_path": "research/projects/joint-action-formation/scenarios/full-line-local-startup-v1.json",
    "source_sha256": "25d471e15c59edc3f120829aec3824c66c22b7cc4fb723ce59213edc69c0e6cd"
  },
  "does_not_authorize": [
    "ACTIVATE_REAL_SCENARIO",
    "CONTACT_REAL_PARTICIPANTS",
    "SEND_CREDENTIALS",
    "SEND_PRIVATE_PARTICIPANT_DATA",
    "SEND_PATENT_DISCLOSURE_TEXT",
    "CREATE_PAID_RESOURCES",
    "REGISTER_SCOPED_MECHANISM",
    "VALIDATE_SCOPED_MECHANISM",
    "PROMOTE_STABLE_CLAIM",
    "EXECUTE_REAL_EFFECT",
    "DEPLOY_OR_PUBLISH"
  ],
  "rationale": "用户持续 Goal 要求全线研究启动。本场景为十条 V2 scoped lines 提供统一的本地、可逆、无真人、无生产研究边界，并明确强标准/平台/中心/人类流程基线、负结果和跨线不可晋升规则。"
}
```
<!-- research-decision:end -->

本场景取代 NAC 专用场景成为 NOW 的当前执行入口；NAC v1/v1.1 场景继续作为精确历史快照
保留，不被覆写。

## 2026-07-28 — 采用“现有技术优先、非独占导向”的研究方向

<!-- research-decision:start -->
```json
{
  "decision_id": "DEC-2026-07-28-EXISTING-TECH-FIRST",
  "status": "APPROVED",
  "decided_by": "USER",
  "actions": [
    "ADOPT_RESEARCH_DIRECTION"
  ],
  "target": {
    "kind": "ResearchDirection",
    "id": "EXISTING-TECH-FIRST-NON-EXCLUSIVITY",
    "version": "v1",
    "source_path": "research/projects/joint-action-formation/studies/existing-technology-first-2026-07-28.md",
    "source_sha256": "0b19925d3d5770dd935811340aea7a64074bcebe75276f3a6c3d12afb69b5ebe"
  },
  "required_rules": [
    "DO_NOT_OPTIMIZE_FOR_TOWOW_ORIGINALITY_EXCLUSIVITY_OR_SPECIALNESS",
    "ADOPT_EXISTING_SOLUTIONS_WHEN_THEY_FULLY_SATISFY_THE_ORIGINAL_NEED",
    "BUILD_THE_STRONGEST_FAIR_EXISTING_TECHNOLOGY_COMPOSITION_BASELINE",
    "LOCATE_THE_FIRST_REPRODUCIBLE_RESPONSIBILITY_BREAK_BEFORE_PROPOSING_AN_EXTENSION",
    "DISTINGUISH_TECHNICAL_COMPOSITION_IMPLEMENTATION_ECONOMIC_INSTITUTIONAL_ADOPTION_AND_NON_DELEGABLE_GAPS",
    "CLOSE_OR_DOWNGRADE_TOWOW_CLAIMS_WHEN_EXISTING_COMPOSITIONS_ARE_EQUIVALENT_OR_BETTER",
    "COMPARE_END_TO_END_LIFECYCLE_NET_VALUE"
  ],
  "does_not_authorize": [
    "CLAIM_EXISTING_TECHNOLOGIES_DO_NOT_SOLVE_THE_PROBLEM_WITHOUT_A_FAIR_COMPOSITION_TEST",
    "CLAIM_TOWOW_IS_NECESSARY_OR_UNIQUE",
    "REGISTER_SCOPED_MECHANISM",
    "VALIDATE_SCOPED_MECHANISM",
    "PROMOTE_STABLE_CLAIM",
    "CONTACT_REAL_PARTICIPANTS",
    "EXECUTE_REAL_EFFECT",
    "DEPLOY_OR_PUBLISH"
  ],
  "rationale": "用户明确校正：通爻独占不重要，能够用现有技术实现就可以；真正承重的问题是既然这些能力都存在，为什么它们仍没有解决原始问题。后续研究因此以最强现有组合、责任闭环和端到端净价值为基线，不再以证明通爻特别为目标。"
}
```
<!-- research-decision:end -->

本决定改变的是研究评价标准，不预先判断存在通爻缺口。若最强现有组合完整解决原始问题，
应直接采用并关闭相应新机制主张；只有可复现的剩余责任断点才允许提出最小扩展。

## 2026-07-28 — 校正为“解决方案优先，组合成果属于通爻”

<!-- research-decision:start -->
```json
{
  "decision_id": "DEC-2026-07-28-SOLUTION-FIRST-COMPOSITION",
  "status": "APPROVED",
  "decided_by": "USER",
  "actions": [
    "CORRECT_RESEARCH_VALUE_FUNCTION",
    "ADOPT_SOLUTION_FIRST_COMPOSITION_METHOD"
  ],
  "target": {
    "kind": "ResearchDirection",
    "id": "SOLUTION-FIRST-COMPOSITION-AS-TOWOW",
    "version": "v2",
    "source_path": "research/projects/joint-action-formation/studies/solution-first-composition-method-correction-2026-07-28.md",
    "source_sha256": "f3e216e33a66d9bede78ba5662dd3a4eaab3dd004d1a624ca8f61e666c3a5098",
    "corrects": [
      "DEC-2026-07-28-EXISTING-TECH-FIRST"
    ]
  },
  "required_rules": [
    "SOLUTION_OF_THE_V1_V2_PROBLEM_IS_THE_PRIMARY_VALUE",
    "GENERAL_MODEL_CENTRAL_SYSTEM_EXISTING_TECHNOLOGY_OR_COMPOSITION_SUCCESS_IS_A_POSITIVE_TOWOW_RESULT",
    "ADOPTED_COMPONENTS_AND_THEIR_REPRODUCIBLE_COMPOSITION_BECOME_PART_OF_THE_TOWOW_SOLUTION",
    "ONLY_THE_NEED_TO_INVENT_A_DUPLICATE_MECHANISM_MAY_CLOSE_NOT_THE_SOLUTION_VALUE",
    "READ_V1_V2_CONDITIONS_BEFORE_ASSIGNING_ANY_TECHNOLOGY_TO_A_LINE",
    "DO_NOT_TREAT_RAG_A2A_ARD_OR_ANY_POPULAR_TECHNOLOGY_AS_A_DEFAULT_ANSWER",
    "EACH_MOTHER_LINE_REQUIRES_ITS_OWN_MULTI_AGENT_RESEARCH_SYSTEM",
    "GROUND_THEORY_METHODS_AND_SIMULATION_IN_ACTUAL_TASKS_AND_MEASURE_SINGLE_AND_COMBINED_COVERAGE",
    "DISCOVERY_AND_CONSTRUCTION_PRECEDE_FORMALIZATION_IN_EARLY_RESEARCH",
    "RECORD_PRIOR_ERRORS_CAUSES_SIGNALS_AND_NON_RECURRENCE_GATES"
  ],
  "does_not_authorize": [
    "START_NEXT_RESEARCH_ROUND",
    "PROMOTE_STABLE_CLAIM",
    "CONTACT_REAL_PARTICIPANTS",
    "EXECUTE_REAL_EFFECT",
    "DEPLOY_OR_PUBLISH"
  ],
  "rationale": "用户指出上一版仍把强中心、通用模型或现有组合解决问题当成通爻增量为零、方案降级或失败，这是错误评价函数。只要某种技术或组合在 V1/V2 条件下解决问题，并能准确复现、复用、迁移和泛化，它本身就是通爻协议的成果。新机制必要性可以被关闭，但采用的能力、组合方法、条件、接口、复现和迁移体系应进入通爻解决方案。用户同时要求每条母线建立自己的多 Agent 研究体系、由实际任务持续牵引、前期奖励发现与构造，并记录历史错误及防复发门。"
}
```
<!-- research-decision:end -->

本决定保留上一版“不要追求原创或独占”的正确部分，但纠正其价值含义：`ADOPT`、
`COMPOSE`、强中心、通用模型、adapter 或最小创新组合完整解决原问题，都是通爻的正向成果。
它们只可能取消重复造新机制的必要性，不能被描述为“通爻价值为零”或从解决方案中移除。

## 2026-07-28 — 启动七母线解题研究

<!-- research-decision:start -->
```json
{
  "decision_id": "DEC-2026-07-28-START-SEVEN-LINE-SOLUTION-RESEARCH",
  "status": "APPROVED",
  "decided_by": "USER",
  "actions": [
    "START_RESEARCH_PROGRAM",
    "START_ALL_SEVEN_MOTHER_LINES",
    "USE_PER_LINE_MULTI_AGENT_RESEARCH",
    "CONTINUE_THEORY_METHOD_IMPLEMENTATION_SIMULATION_AND_SYNTHESIS"
  ],
  "target": {
    "kind": "ResearchProgram",
    "id": "SEVEN-LINE-SOLUTION-RESEARCH",
    "version": "2026-07-28",
    "source_path": "research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/PROGRAM.md",
    "source_sha256": "580938c57cc054973758e414ca21330f870ad916e842b516c773afe23cbd077b"
  },
  "bound_inputs": [
    {
      "role": "AGENT_MARKDOWN",
      "path": "AGENTS.md",
      "sha256": "9cca9b2166aa9de0415d57f0e60d2d2b118a00760634a251623db9b91e2f9611"
    },
    {
      "role": "NAC_SEVEN_ARCHIVE_CLOSURE",
      "path": "research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/nac-seven-archive-manifest.json",
      "sha256": "a3c7af91664db01f7e6fe35b4e4d158b8fea28c441409b3ee6654c6754c80d5c"
    }
  ],
  "seven_goals": [
    "G1-DISCOVERY-BEFORE-SEARCH",
    "G2-RELATION-FROM-TASK",
    "G3-FORM-REACHABILITY",
    "G4-CAPABILITY-TO-RELIANCE",
    "G5-AUTHORITY-COMPOSITION",
    "G6-EFFECT-THAT-COUNTS",
    "G7-REUSE-AND-SAFE-REOPEN"
  ],
  "required_rules": [
    "AGENT_MARKDOWN_MEANS_THE_ROOT_AGENTS_MD_INSTRUCTION_CARRIER_NOT_AGENTOS",
    "SOLVING_V1_V2_WITH_EXISTING_OR_COMPOSED_TECHNOLOGY_IS_A_POSITIVE_TOWOW_RESULT",
    "INDEXING_AND_RETRIEVAL_DO_NOT_SOLVE_PRE_QUERY_UNDECLARED_OR_DISCLOSURE_FRONTIER_PROBLEMS",
    "EACH_MOTHER_LINE_USES_DISTINCT_PROBLEM_DISCOVERY_CONSTRUCTION_ATTACK_EXPERIMENT_AND_SYNTHESIS_DUTIES",
    "SINGLE_AND_COMBINED_SOLUTIONS_USE_THE_SAME_FROZEN_TASK_DENOMINATOR",
    "EXTERNAL_TECHNOLOGY_REQUIRES_LIFECYCLE_FORMAT_SECURITY_LOCK_IN_MIGRATION_AND_SELF_HOST_AUDIT",
    "WHEN_INNOVATION_IS_NEEDED_SOLVE_THE_BOUNDED_GAP_COMPLETELY",
    "HISTORICAL_ERRORS_REQUIRE_CAUSE_SIGNAL_AND_BLOCKING_ACTION",
    "REAL_WORLD_RESOURCE_LIMITS_DO_NOT_STOP_THEORY_METHOD_IMPLEMENTATION_OR_SIMULATION"
  ],
  "does_not_authorize": [
    "SEND_PATENT_DISCLOSURE_TEXT",
    "SEND_PRIVATE_PARTICIPANT_DATA",
    "CONTACT_REAL_PARTICIPANTS",
    "EXECUTE_REAL_EFFECT",
    "PROMOTE_STABLE_CLAIM",
    "REGISTER_OR_VALIDATE_MECHANISM",
    "DEPLOY_OR_PUBLISH"
  ],
  "rationale": "用户明确要求在准备当前问题、五件激活包、继承审计、Agent Markdown 与 NAC 七档案后，立即启动七条母线并持续深入理论、方法验证、实现、模拟、反例和综合；同时逐字校正此前误听：这里是 agent.markdown/Agent Markdown，不是 AgentOS。"
}
```
<!-- research-decision:end -->

本决定启动的是本地、可逆、可持续的研究纲领。六个共同任务含档案任务设计、高保真模拟、
负控和漂移重放，证据级别已分别冻结；它们不能冒充真人事件或生产结果。专利交底书只作为
本地 NAC 研究输入，不进入任何第三方 payload。
