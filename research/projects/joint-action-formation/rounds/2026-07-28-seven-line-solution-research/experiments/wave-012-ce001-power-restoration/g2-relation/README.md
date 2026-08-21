# CE-001 G2 signed owner-process relation module

本模块只产生 G2 owner-native evidence 与 RelationVersion 派生快照，不产生绿色总状态。

## 运行边界

- controller 只读取 `fixtures/endpoints.json` 中的 endpoint/source descriptor，不读取
  `profiles/*.json`；
- `O_Q/O_V/O_R/O_S/O_P` 分别由五个持久 subprocess 运行，每个进程只加载自己的 profile，
  并在进程内生成独立 Ed25519 private key；
- controller 核对 ready manifest PID 与实际 child PID，并强制五 owner 的 PID、
  process instance、key id 与 public key 分别唯一；collision 在任何 query 前 fail closed；
- 每个 receipt 对 canonical raw bytes 签名，preimage exact 绑定 owner、episode、完整
  `Q id/version/hash`、object、purpose、request/response schema、requested/response kind、
  canonical wire request bytes/base64/SHA-256、request payload SHA-256、endpoint、
  episode-specific operation IDs、relation schema hash、global/per-process ordinal、
  nonce/freshness、decision/scope/payload、PID、process instance、key 与 worker source；
- controller 必须验证 raw bytes、SHA-256、Ed25519 signature、public manifest 和全部 exact
  binding；stale/future/replay、ordinal 跳跃、wrong-kind 与 payload/op-id/schema substitution
  均 fail closed。摘要不替代签名；
- RelationVersion 先计算五 owner exact constitution closure。未闭合时只能是
  `DERIVED_CANDIDATE_WITH_UNRESOLVED_CONSTITUTION`，`relation_established=false`、
  `downstream_relation_gate_open=false`，不得生成 `AUTHORIZE/ACTIVATE` intent；
- 闭合后的 local fixture snapshot 仍明确
  `NOT_AN_OWNER_ACT / NOT_AUTHORITY / NOT_EFFECT / NOT_ACCEPTANCE / NOT_SETTLEMENT /
  NOT_CONTRACT_SUCCESS`；
- 缺 policy 保持 `Unknown`；refusal 与 blocking opposition 阻断对应 owner 的 downstream
  authorization/activation intent；
- `authorized/activated` 只输出 `G5_UNVERIFIED` / `G6_UNVERIFIED_NO_EFFECT`。

T5 不接受 `platform_direct_applicable` 裸布尔。独立 local fixture process 必须返回已签名
的 capability proof，再返回 exact proof/object-bound capability readback；任一缺失、错
Q、错 object、坏签名或错误 hash 都 fail closed。readback 只证明平台原生 capability
自配置 fixture 的请求—响应自洽，分类固定为
`LOCAL_FIXTURE_SELF_ASSERTION_VERIFIED`，不建立真实 platform identity/applicability。

Owner 与 platform worker 的 key 都是 child 启动时自生成的 ephemeral key；manifest、
receipt 和输出固定声明 `LOCAL_SYNTHETIC_EPHEMERAL_SELF_KEY`。因此 real owner/platform
identity、Authority 与 legal sufficiency 均为 `NOT_ESTABLISHED`，不是现实 PKI 或 pinned
trust root。G2 handoff 使用 line-local allowlist envelope，`contract_fields_emitted=[]`，
不透传合同 success、Authority、Effect、Acceptance 或 Settlement。

## 运行与产物

```bash
python3 -m unittest discover -s tests -v
python3 run.py
```

`run.py` 对 6 个 fixture 场景完整运行两次，并保存：

- `outputs/rerun-1.json`、`rerun-2.json`：全部 receipt、raw bytes、signature 与轴级结果；
- `outputs/raw-trace.json`：query/receipt/verification 的逐条时序；
- `outputs/process-source-manifest.json`：PID、key、source、process instance、profile source
  id/hash 与退出状态；
- `outputs/semantic-rerun.json`：剥离随机 key/time/PID 后的语义复跑比较；
- `outputs/summary.json`：计数、digest、复跑结论和真实性边界。

当前只运行 local synthetic ephemeral-self-key process。真人 owner、真实平台身份与适用性、
Authority、法律充分性均未建立；target-native Effect、Acceptance、Settlement 仍为
`NOT_RUN`。G5/G6 仍为 `UNVERIFIED`；完整 CE-001、真实 CMMN/CLM/IAM/workflow/HITL/平台
产品均未运行。
