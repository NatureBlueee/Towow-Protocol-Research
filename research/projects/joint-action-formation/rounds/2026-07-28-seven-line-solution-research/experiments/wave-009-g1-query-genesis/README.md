# Wave 009 — T1-HW-C / QUERY-GENESIS-DISCOVERY

## 第二轮审计修复后的精确结论

本轮现在实际运行了一个**内部合成 query-genesis formation**：

```text
vague value seed
→ parent-owned Principal clarification API
→ policy-permitted facet disclosures
→ candidate assembles QueryDraft
→ Principal acceptance
→ signed SemanticQuery
```

在 **public logical API**、且候选遵守 **cooperative non-reflective** 假设时，候选
初始只接收：

```text
VagueValueSeed(
  origin=requester:A,
  value="timely confidential language help"
)
```

该 API 对象没有 `purpose/direction/constraints` 字段。候选必须请求
`PURPOSE/DIRECTION/CONSTRAINTS/VERSION` 澄清并自行组装 draft；错误 direction 得到
`QUERY_REJECTED_BY_PRINCIPAL`。broker 与独立 evaluator 分别实现 acceptance。

因此当前状态为：

```text
QUERY_GENESIS=LOCAL_SYNTHETIC_RUN
```

这不是把预结构化 `PublicGoal` 原样签名，也不声称真实 Principal 形成已运行。
但 Python 同进程反射可以沿 gateway bound dispatch 访问 `ParentRuntime` 及 hidden
world；因此“只见 vague seed”不是进程隔离事实，也不列为 hostile hard gate。

## 冻结形成失败

- `N-NO-FACT`：`CLARIFICATION_AMBIGUOUS`；
- `P-NO-PREDICATE`：`PRINCIPAL_REFUSED_CLARIFICATION`；
- `Z-EXISTS/Z-ABSENT`：相同 `ZERO_DISCLOSURE`。

所有世界具有相同 public value seed 与 initial transcript。`N` pair 的
`D_actual` 不同；`Z` pair 的 latent 不同但全部可观察 transcript 相同。

独立 evaluator 从 records、Principal acceptance 和实际政策构造 action/observation
graph，以 reachability 计算：

```text
L=14
D_actual=10
H=10
```

truth SHA-256：

`5934fd535dc7e028b0e05aa479a43cead542b1f516edda4df2678ffdee686c20`

## 完整解比较

优化强中心与 Router 拥有相同 API、clarification 和短路机会：

| arm | recall | robust safety | cost | latency | disclosure | leakage |
|---|---:|---:|---:|---:|---:|---:|
| optimized strong center + local oracle | 1.00 | 1.00 | 186.0 | 198.0 | 7 | 368 bits |
| Router composition | 1.00 | 1.00 | 186.0 | 198.0 | 7 | 368 bits |

精确结果：

`CAUSALLY_IDENTICAL_UNDER_FROZEN_MATRIX`

不声称 Router 成本优势或 candidate-only advantage。

## Q 四态

broker 与 evaluator 共用 `SignedAuthorityEvidence` 验证器，统一验证 kind、fixture
signature、signer、version/nonce，以及绑定 query
purpose/direction/constraints 的 semantic scope：

| state | required construction |
|---|---|
| `UNEXPRESSED` | local truth + permitted signed projection |
| `UNKNOWN` | valid scoped observer timeout |
| `UNWILLING_TO_DISCLOSE` | valid scoped Authority refusal |
| `ABSENT` | valid scoped completeness + negative attestation |

malformed kind 或 unrelated scope 在 evaluator 中是 `UNKNOWN`，broker 返回
`INVALID_AUTHORITY_EVIDENCE`，不能生成冻结四态。

`R-ONE-SIDED` 保留 matching latent resource，并由对方 Authority 签名拒绝。

## Evidence 与 current heads

qualified evidence 和 receipt 绑定：

- query/detection semantic scope 与 query fingerprint；
- source、principal、version/current head；
- current goal/query-version head；
- expiry 与 runtime nonce。

`S-REVOKED` 在资格化后同时发生 record head 与 goal/query head `v1→v2`；旧 evidence
返回 `GOAL_QUERY_HEAD_ADVANCED`。

其他 gate：

- expiry → `EVIDENCE_EXPIRED`；
- cross-runtime replay → reject；
- sequential duplicate → `EVIDENCE_ALREADY_CONSUMED`；
- 同次 `handoff(ref, ref)` → atomic `DUPLICATE_REFERENCE_IN_HANDOFF`，无 receipt；
- 成功 handoff exact-once；
- handoff 永远是 `CANDIDATE_NOT_COMMITMENT`，不晋升 G2/authority/capability。

## T5 内部合成负控

T5 是父拥有的 **internal synthetic state machine**：

```text
DIRECT: IDLE → VALIDATED → EXECUTED → READBACK_CONFIRMED
NO_MATCH: IDLE → VALIDATED → NO_MATCH → READBACK_CONFIRMED
```

只允许父 registry 中的 `canonical_task_queue`。未注册 target domain 返回
`UNREGISTERED_TARGET_DOMAIN`，before/after 相同，无 effect。这里不扩写成独立外部域。

## Seals

父 seal 绑定：

- world records/policies、cost table、target-domain registry；
- strategy registry/version 与具体 strategy code identity；
- evaluator/world/broker/Authority-evidence model versions；
- operation log、clarifications、queries、current heads；
- 完整 runner/evaluator/broker/strategy 等模块文件内容；
- 当前包内模块定义的全部 function code objects；
- `ParentRuntime`、`CandidateGateway` 及其他包内 class 的全部当前 callable/property
  code objects，由系统遍历产生，不维护易漏的方法白名单。
- consumer module 实际引用的 imported callable aliases；例如 `evidence.py` 消费的
  `verify_authority_evidence`、`semantic_scope` 绑定。
- code constants 的 canonical serialization，包括 `set`、`frozenset`、`dict` 与
  nested code objects；独立 Python 进程生成相同 preimage。

这里的 “method replacement” 精确指 class/module binding replacement。替换
`ParentRuntime._request_handoff`、此前未列入旧白名单的
`ParentRuntime._valid_query`，或重绑定上述 imported aliases，都会使已生成 seal
失效。instance-level shadowing（如给单个 runtime 实例挂同名属性）、直接替换 seal
verifier 与同权限恶意进程不属于 trusted-parent threat model；该机制也不是 hostile
same-process 隔离证明。

## 复现

```bash
python3 -m unittest discover -s tests -v
python3 -m query_genesis
```

当前 31 个测试。详情：

- [RESULTS.md](RESULTS.md)
- [FAILURE_HISTORY.md](FAILURE_HISTORY.md)
- [AUDIT_REPAIR_HISTORY.md](AUDIT_REPAIR_HISTORY.md)

## 边界

- `evidence_status=LOCAL_SYNTHETIC_SAME_AUTHORING_STREAM`；
- `real_world_effectiveness=UNKNOWN`；
- `T4_FULL_JOINT_BID=NOT_RUN`；
- `G2_COMMITMENT_FORMATION=NOT_RUN`；
- `candidate_only_advantage=NOT_ESTABLISHED`；
- `external_calls=0`；
- `hostile_same_process_isolation=false`；
- `same_process_reflection_can_reach_parent_hidden_world=true`；
- vague-seed visibility 只属于 cooperative non-reflective public logical API contract，
  不是安全 hard gate。
