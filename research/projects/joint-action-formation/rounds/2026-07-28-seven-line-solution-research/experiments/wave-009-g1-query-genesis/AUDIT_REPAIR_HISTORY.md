# Independent-audit repair history

原始失败历史保留在 [FAILURE_HISTORY.md](FAILURE_HISTORY.md)。本文件只记录独立审计
之后的新阻断、修复和结论变化。

## AR-0 — 审计回归首先因独立 evaluator 尚不存在而失败

加入审计要求的测试后第一次运行：

```text
ModuleNotFoundError: No module named 'query_genesis.evaluator'
Ran 1 test
FAILED (errors=1)
```

这次红测冻结了新要求，而不是让旧实现继续以相同口径自证。

## AR-1 — content-free refs 与 mode-label circularity

### 审计缺陷

旧 query 只有 opaque ref，没有 origin/purpose/direction/constraints/version 的任务
语义。index/private response 由 hidden mode 直接决定；truth derivation 又读取相同 mode，
无法排除 label leakage 或 evaluator/broker circularity。

### 修复

- 引入父签名 `SemanticQuery` 和 `SemanticProjection`；
- index、predicate、本地 fact 分别保存独立 semantic records；
- broker 实际执行 semantic/constraint match；
- 任何 query 内容篡改、跨 runtime 或来源伪造都拒绝；
- 新 `evaluator.py` 从 records/policies 构造 action/observation graph，再以 BFS
  reachability 计算 `D_actual/H`；
- evaluator 源码禁止读取冻结结果标签。

### 结论变化

`L` 从旧结果的 11 调整为 14，因为动态撤销、拒绝披露和单边拒绝现在诚实保留“资源存在”
而不是把它们写成不存在。`D_actual=10`、`H=10` 保持。

## AR-2 — paired-world denominator 与 label leakage

### 修复

所有世界现在拥有相同 public goal/initial transcript：

- `N-NEW-FACT/N-NO-FACT` 的 `D_actual` 不同；
- `Z-EXISTS/Z-ABSENT` 的 latent 不同，全部可观察 transcript 相同。

主 recall 只读取独立 evaluator 的 `D_actual`，候选不见 world/truth ID。

## AR-3 — Q state 由直接标签返回

### 修复

删除 gateway response 中的 expected boundary。四状态分别改成真实 evidence
constructor：

- local truth + permitted signed projection；
- Authority offline/timeout；
- Authority signed refusal；
- closed-population completeness + negative attestation。

独立 evaluator 只根据 Authority、签名、scope 与闭集条件推导 expected state。

## AR-4 — 强中心比较不公平

### 审计缺陷

旧强中心无条件穷举所有 provider，Router 可以短路，因此 Router 的成本优势主要来自策略
调度差异。

### 修复

强中心获得同样的 API 与短路顺序。两个类保留独立源码/code identity，但冻结矩阵上的
causal trace、recall、安全、cost、latency 与 disclosure 完全相同。

### 结论变化

撤回 Router 成本优势：

```text
strong center: cost=166.5, latency=182.0, leakage=368
Router:        cost=166.5, latency=182.0, leakage=368
```

## AR-5 — qualification 与 handoff 之间没有动态撤销

### 修复

- qualified evidence/receipt 绑定 semantic scope、source、principal、version、
  current head、expiry 与 nonce；
- handoff 必须重新读取 current head 和当前政策；
- `S-REVOKED` 先产生 `CURRENT_COMPAT`，随后 version/head 变化；
- handoff 返回 `POST_QUALIFICATION_REVOKED`；
- 增加 expiry、cross-runtime replay、duplicate 与 exact-once tests。

## AR-6 — T5 completion 只是候选 terminal

### 修复

父 runner 执行 canonical platform state machine，并记录 target-domain before/after：

- direct case 写入 `canonical_task_queue` 后 readback；
- no-match case 对 canonical absence 做 readback；
- gate 要求每个 arm 恰有两条 parent state-machine evidence，不能以空列表通过；
- 候选自报 completion 不进入可信结果。

## AR-7 — 行为独立性与 seals 的 P1 修复

- causal behavior signature 不再包含 trial/world ID；
- 分开报告 implementation code identity 和 causal equivalence class；
- 优化中心/Router 被诚实登记为同一 causal class；
- seal 绑定真实 strategy code identity、evaluator code identity、world/policy、
  cost table、registry/model versions、operation log、queries 与 current heads；
- 明确 `hostile_same_process_isolation=false`。

## 修复后验证

```text
21 tests
all gates PASS
external_calls=0
```

完整输出仍可通过 `python3 -m query_genesis` 重建。现实有效性保持 `UNKNOWN`，
T4/G2 保持 `NOT_RUN`。

---

# Second-review repair

## SR-0 — 第一轮 semantic query 仍不是 query genesis

同一审查者指出：第一轮仍由父 runner 预置完整 `PublicGoal`，候选只是收到结构化字段的
签名副本。因此此前 query-genesis claim 仍然 OPEN。

第二轮审计测试首次运行：

```text
ModuleNotFoundError: No module named 'query_genesis.authority_evidence'
Ran 1 test
FAILED (errors=1)
```

该失败保留为第二轮 tests-first 起点。

## SR-1 — Vague seed 到 candidate draft

candidate-visible `PublicGoal` 已删除。新链路：

```text
VagueValueSeed
→ request_principal_clarification(facet)
→ PrincipalClarification[]
→ candidate-owned QueryDraft
→ Principal acceptance
→ signed SemanticQuery
```

错误 direction 会被 Principal 拒绝。独立 evaluator 另行实现
`principal_accepts_query`。冻结 `AMBIGUOUS/REFUSED/ZERO_DISCLOSURE` 形成失败。

据此保留 `QUERY_GENESIS=LOCAL_SYNTHETIC_RUN`；没有为了保留名称而继续使用预结构化
输入。

## SR-2 — Goal/query-version head

query、qualified evidence 与 receipt 绑定 current goal/query-version head。
`S-REVOKED` 资格化后从 v1 变为 v2，旧 evidence 返回
`GOAL_QUERY_HEAD_ADVANCED`。

## SR-3 — Q evidence 统一验证

新增统一 `SignedAuthorityEvidence` verifier。broker 与 evaluator 都检查 kind、
fixture signature、signer、version/nonce，以及绑定 query
purpose/direction/constraints 的 scope。

malformed kind 或 unrelated scope 在 evaluator 中为 `UNKNOWN`，broker 返回
`INVALID_AUTHORITY_EVIDENCE`，不形成冻结状态。

## SR-4 — Duplicate handoff atomicity

`handoff(ref, ref)` 现在返回 `DUPLICATE_REFERENCE_IN_HANDOFF`，不消费 evidence、不产
receipt；同一 ref 随后仍可单次成功。

## SR-5 — T5 target-domain registry

只注册内部 `canonical_task_queue`。未注册 target domain 返回
`UNREGISTERED_TARGET_DOMAIN`，before/after 相同。全部结果明确标记
`INTERNAL_SYNTHETIC`，不扩写为外部域。

## SR-6 — Executable-preimage seal

seal 现在绑定完整模块文件、关键 `ParentRuntime` method bytecode、
`semantic_compatible`、Principal acceptance、Q constructors、runner/evaluator
scoring。bundle 生成后替换 `_request_handoff` 会使原 seal 失效。

## 第二轮结果

```text
27 tests PASS
QUERY_GENESIS=LOCAL_SYNTHETIC_RUN
L=14, D_actual=10, H=10
strong center = Router:
  recall=1.0
  robust_safety=1.0
  cost=186.0
  latency=198.0
  leakage=368 bits
```

真实主体、外部 target domain、T4 与 G2 仍未运行；现实有效性保持 `UNKNOWN`。

---

# Final-review repair

## FR-1 — Vague-seed visibility claim 仍过强

最终审查指出，gateway 与 `ParentRuntime` 同进程；反射可以沿 bound dispatch 访问
hidden world。因此“candidate 只见 vague seed”不能作为无条件事实或 hostile hard
gate。

所有当前 claim 已收窄为：

```text
cooperative non-reflective candidate
over the public logical API
```

同时明确：

```text
hostile_same_process_isolation=false
same_process_reflection_can_reach_parent_hidden_world=true
```

该项位于 limitations/security claims，不列为 hostile hard gate。

## FR-2 — Executable-preimage 方法白名单漏绑

新增精确回归：bundle 生成后替换旧白名单没有列入的 `_valid_query`。

旧实现实际失败：

```text
test_unlisted_valid_query_replacement_also_invalidates_seal ... FAIL
AssertionError: True is not false
Ran 1 test
FAILED (failures=1)
```

根因是 executable preimage 只枚举人工维护的关键方法名。

修复后不再维护方法白名单，而是系统遍历：

- 当前包内模块定义的全部 function code objects；
- `ParentRuntime`、`CandidateGateway` 及所有包内 class 的全部当前
  callable/property code objects；
- nested code objects、defaults 与 kwdefaults；
- 同时保留完整模块文件内容哈希。

替换 `_valid_query` 或 `_request_handoff` 都会使旧 bundle 验证失败。

边界没有扩大：直接替换 seal verifier 或同权限恶意进程仍不在保证内。

## 最终回归

最终验证：

```text
28 tests PASS
truth_sha256=
5934fd535dc7e028b0e05aa479a43cead542b1f516edda4df2678ffdee686c20
```

核心 claim 仍是 cooperative non-reflective public API 下的内部合成 query genesis，
不是安全隔离或现实 formation。

## FR-3 — 消费别名与跨进程 canonical preimage

最终有界复核新增三项回归。修复前的实际失败为：

```text
test_consumed_verify_authority_alias_rebinding_invalidates_seal ... FAIL
test_consumed_semantic_scope_alias_rebinding_invalidates_seal ... FAIL
test_executable_preimage_is_stable_across_python_processes ... FAIL
Ran 3 tests
FAILED (failures=3)
```

前两项说明：仅绑定 callable 定义者模块仍会漏掉 consumer module 实际使用的 imported
alias；重绑定 `evidence.verify_authority_evidence` 或
`evidence.semantic_scope` 后，旧 bundle 仍能通过。

第三项说明：以 `repr(co_consts)` 表示包含 `frozenset` 等无序常量时，两个独立
Python 进程产生不同 preimage。

修复后：

- 系统遍历每个 consumer module 本地 callable 的 `co_names`，只绑定其中实际引用的
  imported callable aliases；
- 对 code constants、defaults 与 kwdefaults 使用递归 canonical serialization；
- `set`、`frozenset` 和 `dict` 按 canonical JSON 排序，nested code objects
  递归绑定；
- 两个独立 Python 进程生成相同 executable preimage。

威胁边界保持不变：这里检出的 “method replacement” 只指 class/module binding
replacement。instance-level shadowing、直接替换 seal verifier 和同权限恶意进程不在
trusted-parent threat model，也不构成 hostile same-process hard gate。

本轮最终回归为：

```text
31 tests PASS
truth_sha256=
5934fd535dc7e028b0e05aa479a43cead542b1f516edda4df2678ffdee686c20
executable_preimage_sha256=generated by build_report(); intentionally not pinned here
```
