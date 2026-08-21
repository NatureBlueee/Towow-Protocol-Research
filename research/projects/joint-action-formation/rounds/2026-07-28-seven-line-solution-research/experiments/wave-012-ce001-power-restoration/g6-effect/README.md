# CE-001 G6 Effect / Acceptance / Settlement

状态：`LOCAL SYNTHETIC FIVE-OWNER-PROCESS COMPONENT + LOCAL SYNTHETIC E2E /
REAL PRODUCT NOT_RUN`

这个目录只回答 CE-001 的 G6 局部问题：

- raw occurrence、episode binding、Authority、`CountsTowardQ`、recovery 分开；
- pre-existing state 不冒充 exact attempt causality；
- wrong-target damage 保留为真实 Effect，即使它不计入 Q；
- Effect、Adoption、requester Acceptance、venue Acceptance 分属不同 owner；
- Settlement 是 O_P 的 obligation / scheme / finality / reversal subgraph，不是一个全局 bool；
- method 只持有 owner API capability，逐项取得 observation，不接收完整 owner packet、
private expected label 或 evaluator truth。

第二轮根红灯修复后，`O_S / O_E / O_Q / O_V / O_P` 是五个由 `spawn` 启动的独立 OS
process。每个 process 只收到自己的 state shard；method-visible `OwnerClient` 只持有五条
public RPC pipe，不持有 callable、world、owner state 或 admin/snapshot pipe。请求与响应均为
canonical JSON bytes，响应绑定 exact request hash、owner、endpoint 和 process ID；raw trace
保留实际 transmitted bytes 与双向 SHA-256。

第三轮进一步关闭 response currentness 假闭包。每个 request/response 现在同时绑定
canonical request bytes/hash、owner/endpoint、session、owner instance、实际 owner PID、
client PID、nonce、ordinal，以及 worker dispatch 后的 native state/ledger heads 和
native record refs。`G6Method` 不再调用 detached payload decoder；只有当前
`OwnerClient` 本次 run 后登记且尚未消费的 response receipt 才能进入语义投影。跨 session、
跨 owner、跨 endpoint、跨 request，以及同 session 旧 ordinal replay 均 fail closed。

worker 先运行真实 native dispatcher、写入 owner shard 的 domain record，再独立形成
attestation；`response_overrides` 只能替换 transport payload，不能改写 native proof。
O_Q/O_V native act record 绑定 exact Effect digest、episode/Q 与 current request；
O_P record 绑定 exact Acceptance set hash、Effect、obligation、scheme/phase set 和 current
request；O_E record 绑定 occurrence/target/recovery readback。recovery_state 与 target_state
仍是同一 O_E 来源，当前保证来自最终 native shard/ledger seal，不称独立来源。

evaluator 显式接收冻结的 `trace_closure` 与 runner 从实际 public plan 重算的
`expected_plan_sha256`。runner 在 owner session 关闭前冻结 plan hash、result hash、raw
request/response bytes、receipt order、native head chain；drop、reorder、byte tamper、
plan/result transplant 或 detached result 均拒绝。G6 仍不声称 hostile grader blindness。

`O_Q` 与 `O_V` 分别在自己的 process 内产生唯一 `act_id` 的 Acceptance。`O_P` 不读取它们
的 state，而是在收到两份 exact、不同 owner/process/act 的 transmitted act 后，独立产生
obligation 与 finality readback。evaluator 的 resolution truth 来自独立的
`grader-input.json`，并由固定 SHA-256 校验；owner simulator 不加载 grader。

`CountsTowardQ` 是派生结果，不是语义压缩点。每个 Effect assessment 同时显式保留
`current_state_matches_q`、`exact_attempt_causality`、
`authority_covers_actual_object` 与 `episode_contribution`。例如预存 C7 供电可以
`current_state_matches_q=true`，但 `exact_attempt_causality=false`；对 C7 的授权也不会覆盖
实际落在 C8 的 occurrence。

Recovery 同样不靠 action receipt 自证：method 先取得 recovery occurrence，再独立查询
O_E target-current-state；只有受损 object 已回到原状态且 readback 不早于 recovery
occurrence，且 target state version 与 recovery occurrence version/last-occurrence 一致，
才允许执行 fallback。reversal occurrence 仍保留在历史中。

G6 不能独立证明合同的 deadline、连续 45 分钟、完整安全约束和跨线 operation 前提。因此
本目录只输出 `g6_line_local_closure` 与明确命名的 `g6_line_local_components`；合同级
`contract_exact_task_success=NOT_COMPUTED_BY_G6`，须由集成 evaluator 重算。

## 两种证据面

```bash
python3 run.py --mode semantic
python3 run.py --mode end-to-end
python3 run.py --mode failure-injection
python3 run.py --mode all
python3 -m unittest discover -s tests -v
```

`semantic` 是结构与反例的 conformance，不执行 CE-001 episode。`end-to-end` 会经由
owner/action APIs 执行八个本地合成 case，并写出 API raw trace。两者的结果和分母不相加。

生成物：

- `artifacts/semantic-results.json`
- `artifacts/e2e-results.json`
- `artifacts/raw-trace.jsonl`
- `artifacts/failure-injection-results.json`
- `artifacts/failure-trace.jsonl`

这里没有真实电路、真人 owner、生产付款 rail 或第三方产品。因此：

```text
SEMANTIC_CONFORMANCE = LOCAL_SYNTHETIC_COMPONENT
END_TO_END_EXECUTION = LOCAL_SYNTHETIC_E2E
REAL_PRODUCT_EXECUTION = NOT_RUN
PRODUCTION_EFFECT = NOT_RUN
HUMAN_ACCEPTANCE = NOT_RUN
PAYMENT_FINALITY = NOT_RUN
CONTRACT_EXACT_TASK_SUCCESS = NOT_COMPUTED_BY_G6
GRADER_BLINDNESS = NOT_ESTABLISHED
```
