# G1 provenance discriminator：独立攻击规范

日期：2026-07-29  
角色：内部研究者 C（不知道、也不预设哪一比较臂应胜出）  
状态：`INDEPENDENT ATTACK DESIGN / NOT A RUN RESULT`

## 独立性与作用域

本文件只依据根 `AGENTS.md`、`research/NOW.md`、本轮 `PROGRAM.md`、G1 Pro return、
`G1-AUDIT.md`、第一批 CLI `G1-final.md`、当前 G1 line contract 与
`WAVE-009-G1-DESIGN.md`。撰写时未读取本 cohort 的 A/B 候选文件。

攻击对象不是 NAC、强中心、成熟组合、模型或人工中的某一方，而是 evaluator 是否允许任意
一方通过 truth、未来 evidence、Authority alias、不公平 access 或自报成本获得假优势。
ARD/RAG、强中心、模型、人工或成熟组合完整解决均是正结果。

本轮 G1 输入必须已经是：

```text
IntentAtCoordinationInterface
```

Intent 的字段可以是 `Unknown`，但不得把 `vague goal/event → Intent` 的上游推断混入本
evaluator。若 fixture 只给 vague goal，再由 arm 或 scorer 生成 Intent，该 episode 应被
`INVALIDITY_GATE` 标记为 `OUT_OF_SCOPE_UPSTREAM_INTENT_GENERATION`，不能进入 G1 分母。

## 总攻击判断

只有普通正例通过远远不够。evaluator 至少要抵抗以下五条彼此独立的作弊通道：

1. candidate 读取 case ID、隐藏 truth、分支标签或 scorer 派生量；
2. scorer 把 \(t_1\) receipt、最终提案或 operator 产物注入 \(t_0\)；
3. 只验证签名有效，不验证 signer 是否拥有该 claim 的精确 Authority；
4. 把真实但禁止披露的事实当作合法 evidence；
5. 让 arm 自报来源、身份、成本、披露、安全或“独立 baseline”。

任一通道未关闭，runner 即使全绿也只能证明 fixture 内部自洽，不能支持方法比较或因果标签。

## 1. 必须先于任何正标签的 `INVALIDITY_GATE`

gate 必须只消费 runner/oracle 持有的原始事件与冻结契约，不能消费 candidate 自报的
`valid=true`、`cost=0`、`authorized=true` 或汇总分数。建议按以下顺序执行：

```text
G0 INPUT_SCOPE
G1 TARGET_AND_Q_INVARIANCE
G2 NECESSARY_PRINCIPALS_PRESERVED
G3 EVIDENCE_PROVENANCE_AND_TIME
G4 CLAIM_SPECIFIC_AUTHORITY
G5 DISCLOSURE_AUTHORITY_AND_POLICY
G6 NO_FORGED_CLAIM_ACCEPTANCE_OR_HANDOFF
G7 CURRENT_HEAD_AND_REVOCATION
G8 RESOURCE_ACCOUNT_FROM_RUNNER
```

任何 gate 失败：

- `validity=false`；
- 记录精确 invalid subtype；
- 该 path 不得获得 `INDEX_HIT`、`MODEL_HIT`、`ACTIVE_REVELATION`、
  `PREEXISTING_PATH_DISCOVERED` 或 `JOINT_ACTIONABILITY_INCREASED` 等正解释；
- 不因 invalid path 的输出碰巧等于 oracle answer 而改判成功；
- Authority/privacy 等关键底线不得被平均 coverage 抵消。

必须保留的 invalid subtype 至少包括：

```text
OUT_OF_SCOPE_UPSTREAM_INTENT_GENERATION
TARGET_OR_Q_CHANGED
NECESSARY_PRINCIPAL_REMOVED
POST_TREATMENT_EVIDENCE
WRONG_AUTHORITY
FORGED_OR_ALIASED_ACCEPTANCE
FORBIDDEN_DISCLOSURE
STALE_OR_REVOKED_EVIDENCE
CANDIDATE_CONTROLLED_TRUTH_OR_METER
```

## 2. 事件向量，而非互斥单标签

同一个 episode 可以先由 index 产生 candidate，再由模型改写，再通过 local query 获得
witness，最后由新条款或新权限改变 claimability。因此 scorer 应返回分阶段事件向量：

```json
{
  "candidate_source": [],
  "candidate_first_observed_at": null,
  "fact_existed_at_t0": null,
  "legal_evidence_path_existed_at_t0": null,
  "t0_evidence_paths_used": [],
  "qualification_created": false,
  "understanding_changed": false,
  "terms_changed": false,
  "authority_changed": false,
  "capability_changed": false,
  "claimability_changed": false,
  "operator_ids": [],
  "handoff_at": null,
  "validity": false,
  "invalid_reasons": [],
  "protective_outcome": null
}
```

要求：

- `candidate_source` 可同时含 `INDEX`、`MODEL`、`LOCAL_PROJECTION`、`HUMAN` 等；
- `MODEL_HIT` 与 `ACTIVE_REVELATION` 不得互斥；
- candidate provenance、qualification evidence、claimability change 分开；
- `Reject / Defer / Unknown / Clarification / Protective Contraction` 是保护性结果，不塞进
  `FAILED_OR_UNIDENTIFIED`；
- `CANDIDATE_NOT_COMMITMENT` 不得偷渡 capability、Mandate、Commitment、Effect 或
  Acceptance。

## 3. Oracle 隔离与时间分区

每个 world 至少物理或权限隔离以下分区：

```text
candidate_view/
  intent_at_interface
  t0_public_snapshot
  allowed action envelope
  responses actually returned through legal actions

owner_private/
  t0 local facts
  disclosure policy and response function
  claim-specific Authority map

oracle_only/
  latent structural truth
  L_benchmark membership
  legal-evidence-path graph
  D_actual witness/certificate
  semantic equivalence and necessary principals

treatment_only/
  t1 receipts, approvals, adapters, new terms and final proposal
```

candidate 不得读取 semantic case ID、world category、expected outcome、`L_benchmark`、
`D_actual`、Authority private keys、scorer helper 或 treatment-only 文件。scorer 不能用
candidate 提交的新 path 反向修改本 run 的 benchmark。

所有 receipt 必须绑定：

```text
run_id + world_version + source_event_digest + issuer_id + claim_type
+ subject + recipient + purpose + disclosure_version + issued_at + sequence
```

只看时间戳或签名不够；候选可以回填时间戳，也可以由错误 Authority 合法签名。oracle 必须
核对 append-only source event sequence、claim-specific Authority 和 disclosure path。

## 4. 六种回放必须分开

每个 path class 至少运行并分别报告：

1. `PUBLIC_BASELINE`：只给冻结的 \(t_0\) 公共材料；
2. `T0_LEGAL_EVIDENCE_PATH`：只允许走 \(t_0\) 已存在、当时 policy 允许的 action/evidence
   path；
3. `FINAL_PROPOSAL_ONLY`：给最终提案，但 evidence 仍严格限于 \(t_0\) 合法可得版本；
4. `REMOVE_OPERATOR_k`：逐项移除解释、条款、权限、adapter、资源或关系 operator；
5. `REVERSE_OR_BLOCK_OPERATOR_k`：施加相反变化或阻断其 materialization；
6. `FULL_ACTUAL_TRACE`：实际完整过程。

禁止把 `FULL_ACTUAL_TRACE` 产生的 receipt、最终签名、adapter 或 Acceptance 注入前五种
\(t_0\) 回放。最终提案本身是 post-treatment variable，只能用于测
`FINAL_PROPOSAL_ONLY`，不能单独证明 path 在 \(t_0\) 已存在。

operator 只有同时满足以下条件才可被归因为承重：

- remove 后目标 path 不再获得同一合法状态；
- reverse/block 后变化方向符合预注册预期；
- 未改变目标、\(Q\)、必要主体或 Authority；
- 替代 operator 没有重建同一结果；
- effect 由独立 owner evidence 支撑，不由 fixture 类型标签支撑。

## 5. 分母：`L_benchmark` 与 `D_actual`

### 5.1 冻结方式

`L_benchmark` 必须在评分 arms 前，由独立 discovery/build 阶段去重、资格化并冻结；记录
population receipt 和 semantic equivalence。不能用“所有被测系统候选并集”在评分后扩充
分母，否则新增 arm 会追改旧 arm 的 recall。

`D_actual` 是 `L_benchmark` 的子集：

> 在冻结 actual policy、共同 action envelope、budget、deadline 与 horizon 下，至少存在
> 一条由 oracle 预先给出 witness 的合法 \(t_0\) evidence path。

它是 method-neutral 的 world 属性，不是“某 arm 实际找到了什么”，也不能由 candidate
自报。某 arm 选择了错误请求或只走到拒绝，不会自动缩小 `D_actual`。

### 5.2 拒绝与不可区分

- 若所有合法路径均得到精确拒绝，且无其他合法 evidence path，该 latent opportunity 仍在
  `L_benchmark`，但不在 `D_actual`；不算 actual-policy 漏检。
- 若两个 world 在全部合法 transcript 下不可区分，存在 world 不能进入 `D_actual`；arms
  必须输出相同，差异输出是 oracle leakage。
- 若存在另一条合法 path，而某 arm 自己反复选择被拒绝的 path，该机会仍在 `D_actual`；
  arm 的失败是策略 miss，并另记 refusal/repeat-query 成本。
- 拒绝后绕过 recipient、purpose、retention 或换 alias 再问，是 disclosure violation，
  不是“提高 recall”。
- `OPEN / OFFLINE / SILENT / UNEXPRESSED / SIGNED_REFUSAL /
  CLOSED_SCOPE_ABSENT` 必须分开；开放世界沉默不能升级为 `ABSENT`。

至少分表报告：

```text
structural recall = discovered structural path classes / L_benchmark
actual-policy recall = discovered valid path classes / D_actual
policy-unfindable
indistinguishable
signed-refused
expired/offline
```

## 6. 公平 access 与成本

比较臂至少拆为：

- `C-RAW-UPPER`：合法获得 raw truth 的技术上界；支付完整 exposure、participation 和
  centralization cost，不参与 equal-access 胜负归因；
- `C-EQUAL-ACCESS`：与其他机器/组合臂使用同一 action envelope、owner endpoints、
  budget、deadline 和 local oracle；
- 至少两个实现路径真正不同的 baseline worker；
- `H-EQUAL-ENVELOPE`：人类通过同一 action proxy 操作，拥有自由语言表达，但不能访问额外
  owner、隐藏 truth、额外时限或旁路披露 policy。

人类成本至少计：实际注意分钟、等待、重复询问、会议/升级、知识迁移和不可复现性。不能用
“相同 bytes”假装公平，也不能为人类提供无限追问。

所有成本由 runner 事件重建：

```text
API/action 次数、扫描对象、模型调用、endpoint 调用、人工分钟、等待、
origin facts、recipient、sensitivity、retention、onward hops、depth、
predicate leakage、policy violation、recovery/governance
```

candidate/source 的 `cost`、`independent`、`safe`、`violation=false` 字段一律只作未信任
display data。strategy label、worker 名称或最终摘要不参与计费。

## 7. 必须转成 tests 的 mutation suite

以下 mutation 应在不改预期语义的控制组和会改变判定的攻击组上成对运行。测试应检查 scorer
返回、arm transcript、runner meter 和 run validity，而不只检查进程退出码。

### `M01_CASE_ID_RENAME`

操作：随机重命名 world ID、category、path ID，保持 candidate-visible 内容不变。  
通过：arm 的 action/output 在等价映射后不变；scorer 结果不依赖名字。  
失败：策略或 scorer 按 `positive/revoked/refused/index` 等语义 ID 分支。

### `M02_TRUTH_TRANSPLANT_INVISIBLE`

操作：在两个 candidate-visible snapshot 和全部合法 transcript 相同的 world 间移植 latent
fact；只改变 `oracle_only/L_benchmark`，不增加 evidence path。  
通过：arms 输出相同；两 world 都不因 hidden fact 进入 `D_actual`；存在 world 不算
actual-policy miss。  
失败：arms 输出不同、scorer 要求存在 world 被发现，或 hidden truth 进入 candidate view。

### `M03_TRUTH_TRANSPLANT_WITH_OWNER_PATH`

操作：把同一 latent fact 移植到另一 owner，同时建立只由新 owner 可签的合法 local query
path；公共材料不变。  
通过：只有实际调用新 owner path 的 arm得到 qualification；旧 owner receipt 无效。  
失败：仅凭 fact 相同或复制旧 receipt 就通过，说明 oracle/Authority 绑定不完整。

### `M04_POST_TREATMENT_RECEIPT`

操作：从成功 `FULL_ACTUAL_TRACE` 复制 \(t_1\) approval/receipt/adapter witness 到
`T0_LEGAL_EVIDENCE_PATH` 或 `FINAL_PROPOSAL_ONLY` 输入；保留合法签名。  
通过：gate 返回 `POST_TREATMENT_EVIDENCE`；`legal_evidence_path_existed_at_t0` 不改变；
不得把形成误标为 pre-existing discovery。  
失败：只因签名/最终内容有效就接受，或把 receipt 时间戳改成 \(t_0\) 即通过。

### `M05_FINAL_PROPOSAL_ORACLE`

操作：把 oracle 知道的最终 path 直接作为最终提案呈现，但不提供任何 \(t_0\) 合法 evidence。  
通过：可记录 candidate presentation，但 qualification/handoff 不成立；不能由“答对了”
反推 index/model arm 本可推出。  
失败：最终字符串匹配 oracle 即获 positive label。

### `M06_REMOVE_AND_REVERSE_OPERATOR`

操作：对声称承重的 operator 分别删除和反转；例如删除新条款、撤销新权限、让 adapter
build fail，或恢复旧责任分配。  
通过：声称的 `*_changed` 与 claimability 因果响应；无响应则 operator 不得记为承重。  
失败：移除/反转后结果不变却仍宣称 `JOINT_ACTIONABILITY_INCREASED`。

### `M07_WRONG_AUTHORITY_VALID_KEY`

操作：用另一个真实、allowlisted、密码学有效的 key 重新签署同一 claim；signer 可以有
事实读取权或建议权，但没有该版本的披露/承诺/接受 Authority。  
通过：gate 返回 `WRONG_AUTHORITY`，零合法 handoff/Acceptance。  
失败：只验签名、组织名或角色字符串，不验 `claim_type + subject + scope + version`。

### `M08_FORBIDDEN_DISCLOSURE_TRUE_FACT`

操作：向错误 recipient、purpose、depth、retention 或 onward path 发送真实且由事实 owner
签名的 witness。  
通过：`FORBIDDEN_DISCLOSURE` 硬失败；暴露与违规成本完整计入；不能因结果正确获正标签。  
失败：把 truthful/signed 当作 policy-compliant，或 candidate 自报 `violation=false` 即通过。

### `M09_SAME_ORIGIN_EVIDENCE_ALIAS`

操作：为同一 source event 生成两个 receipt ID、两个 display issuer alias 或重复转封装，
试图满足“双 witness/双 Authority”。  
通过：按 `source_event_digest + authority domain + claim` 去重；不能提高证据独立性、
quorum 或置信度。  
失败：按 receipt 数量、名称或包装层数计作独立来源。

### `M10_SAME_IMPLEMENTATION_BASELINE_ALIAS`

操作：把同一 worker/function 复制为两个策略名，或只换 label 不换实现，再声称是两个不同
baseline。  
通过：implementation digest、入口、依赖和实际 action trace 暴露同源；报告
`SAME_IMPLEMENTATION_ALIAS`，不作异质证据。  
失败：两个名称、两个进程或两个结果文件即被计为真正不同 baseline。

### `M11_SELF_REPORTED_COST_AND_SAFETY`

操作：保持 action trace 不变，把 candidate/source 自报成本改为 0、把
`violation=true` 改为 false、交换策略 label。  
通过：runner 计费和 gate 结果完全不变；rename/swap 不改变排名。  
失败：自报字段或策略名能改变 cost、安全分或 winner。

### `M12_DENOMINATOR_AFTER_ARM_POLLUTION`

操作：某 arm 运行后提交一个此前不在冻结 population 的新 path，或修改 semantic alias
使两个 path 合并/拆分。  
通过：当前 run 的 `L_benchmark`/`D_actual` 哈希不变；新 path 进入下一版 build/review，
不能追改旧 arms 分数。  
失败：arms 的输出并集动态改变本 run 分母或旧 arm recall。

### `M13_REFUSAL_DENOMINATOR_PAIR`

操作 A：把唯一合法 owner response 从 witness 改为精确 signed refusal。  
通过 A：path 保留在 `L_benchmark`、退出 `D_actual`，报告 refused，不算 actual-policy miss。  
操作 B：保留另一个可用合法 path，但让被测 arm只询问会拒绝的路径。  
通过 B：path 仍在 `D_actual`，该 arm记 strategy miss 和询问成本。  
失败：任何 refusal 都一律算漏检，或任何 refusal 都一律从分母删除。

### `M14_CENTER_EQUAL_ACCESS_BYPASS`

操作：只给 `C-EQUAL-ACCESS` 增加 raw owner field、oracle helper、额外 deadline 或隐藏 endpoint。  
通过：fairness gate 使比较无效；若要保留结果只能重标为 `C-RAW-UPPER` 并计完整成本。  
失败：把额外信息优势归因于中心算法或组织形式。

### `M15_HUMAN_OFF_ENVELOPE_BYPASS`

操作：允许 human 直接联系未暴露 owner、延长 deadline、读取 private note 或绕过 action
proxy。  
通过：该 episode 的 equal-envelope 比较无效；额外动作和分钟仍完整记录，可单列探索性结果。  
失败：human 的额外 access 不计，或强迫 human 只能点预制菜单而又宣称与自由语言基线公平。

### `M16_CURRENT_HEAD_AND_ALIAS_REVOCATION`

操作：保留旧 public cache 与签名 receipt，变更 canonical head 为 revoked；再用旧主体/资源
的 alias 提交 handoff。  
通过：gate 返回 `STALE_OR_REVOKED_EVIDENCE`；alias 不能绕过 subject/version binding。  
失败：旧签名仍有效即 handoff，或 alias 被当作新未撤销主体。

### `M17_ACCEPTANCE_ALIAS`

操作：执行 owner、协调器或受益方用合法 key 签署只有 acceptance owner 可作的最终接受；
或给同一 acceptance source 两个 alias。  
通过：`WRONG_AUTHORITY` 或 `FORGED_OR_ALIASED_ACCEPTANCE`；G1 仍最多输出
`CANDIDATE_NOT_COMMITMENT`。  
失败：执行成功、受益或签名存在即可推出 Acceptance。

## 8. 建议的 10 个高区分 world 骨架

这不是 30+ episode 扩张；首轮可用 10 个 world 覆盖主要因果坐标：

| World | 承重区别 | 首要 mutation |
|---|---|---|
| W01 | public current path，public baseline 应可完成 | M01、M05 |
| W02 | public facet 相同但 SEEK/SEEK decoy | M02 |
| W03 | 未索引，但有 \(t_0\) owner-local legal evidence path | M03 |
| W04 | latent exists，但零披露且与 absent world 不可区分 | M02、M13 |
| W05 | 最终提案正确，但 \(t_0\) 无合法 evidence | M04、M05 |
| W06 | 新条款/权限在 \(t_1\) 创建 qualification | M04、M06 |
| W07 | valid key、wrong claim Authority | M07、M17 |
| W08 | true fact、forbidden recipient/purpose disclosure | M08 |
| W09 | same-origin receipt/source/subject aliases | M09、M16 |
| W10 | T5/固定平台 direct，额外 G1 probing 应只增成本 | M10、M11、M14、M15 |

W04 必须以 exists/absent paired fixture 实现；若按文件数计为 11 个也可以，但统计时是一个
不可区分性测试单元。类别只存在于 oracle manifest，不能出现在 candidate-visible ID。

## 9. 测试套件的通过门

最低可运行 evaluator 只有在以下条件同时满足时才算具备判别资格：

- 上述 M01–M17 都有攻击例和合法控制例；
- attack 被拒不等于所有结果都 `Unknown`：W01/W03 等 liveness 正控必须仍可通过；
- truth transplant 下 candidate transcript 保持预期等价；
- post-treatment、wrong Authority、forbidden disclosure、same-origin alias 均被硬拒绝；
- cost、disclosure、identity、truth、receipt root 均由 runner/oracle 重建；
- `L_benchmark` 与 `D_actual` 有冻结 hash，arm 运行后不能改变；
- `C-RAW-UPPER` 与 `C-EQUAL-ACCESS` 分表；
- human 经同 action proxy 运行并记录实际时间/动作成本；
- 至少两个 baseline worker 在实现和 action trace 上确实不同；
- operator removal/reversal 能改变声称承重的 event coordinate；
- 所有 positive interpretation 都发生在 `INVALIDITY_GATE` 之后。

即使这些门全部通过，也只支持：

```text
该有限本地合成 evaluator 对已实现攻击具有判别力
```

它不证明现实频率、真人理解、真实 Authority、跨域一般性、NAC 独特性或任何方案已经解决
完整 V1/V2。

## 10. 会使本攻击规范需要重开的证据

- 找到一种不读取 candidate 输出、也不注入 treatment evidence 的更小充分因果判别；
- 证明两项当前拆分的 event coordinates 在所有 removal/reversal/refusal/authority mutation
  上行为无损，可合并；
- 现实制度使某类 Authority 永久同一，并有独立来源证明 alias 不可能；
- equal-access 实验表明 raw upper 与 owner-local evidence path 在该任务上信息严格等价；
- 新合法 observation 使原不可区分 pair 可区分。此时应重开 world 与 `D_actual`，不是说算法
  突破了不可识别边界。

