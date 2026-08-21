# Wave 011 G5 Authority Conformance — MCB-G5-v2 discriminator

状态：`COMPLETE_LOCAL_SYNTHETIC_DISCRIMINATOR / NO FORMAL PROMOTION`

## 结论

本目录实现的是一个小型判别器，不是 canonical IR、生产 Authority 服务或新的通用协议。
它把 G5-AUDIT 提出的 MCB-G5-v2 五组实验压成一套可运行的本地夹具，能区分：

- 真正统一 Authority 与“技术权限完全相同、仍有外部 non-delegable right”；
- provider-native outcome 与经任务映射派生的业务四值；
- 四个 owner 的独立 truth/key/process 与免费 registry；
- 单域事务、跨 Authority 协调、2PC-like hold、Saga compensation；
- ledger token 与 target 真正执行 monotonic fence；
- 主对象 digest 与 material operation closure；
- 已知 Standing case 与未预登记主体/late challenge；
- 已运行 corpus 上的 witnessed equivalence 与一般语义等价。

当前运行没有观察到必须新增 G5 协议的稳定 residual。强中心、成熟组件组合、CLM/HITL
和人类规则都保留完整胜出路径；哪一种在同分母上完整解决就是正结果。

## 实际运行状态

| 项目 | 状态 | 最窄含义 |
|---|---|---|
| `LOCAL_REFERENCE_POLICY_ENGINE` | `RUN` | 独立 subprocess 实际执行 7 个 native-outcome case |
| provider adapter shape corpus | `RUN / PRODUCTS NOT RUN` | 13 个 OPA/Cedar/OpenFGA/XACML native shape 只测薄 adapter |
| OPA | `NOT_RUN_ENGINE_NOT_INSTALLED` | 没有产品比较结果 |
| Cedar | `NOT_RUN_ENGINE_NOT_INSTALLED` | 没有产品比较结果 |
| OpenFGA | `NOT_RUN_ENGINE_NOT_INSTALLED` | 没有产品比较结果 |
| XACML | `NOT_RUN_ENGINE_NOT_INSTALLED` | 没有产品比较结果 |
| 四个 owner services | `RUN` | 四个 PID、store、Ed25519 key，独立 reject/revoke/outage/fork |
| race matrix | `RUN` | 5 strategy × 2 Authority stratum × 5 injection boundary |
| target fence matrix | `RUN` | enforce / ignore / restart-loss / cross-region reorder |
| materiality/Standing/migration | `RUN` | 本地 fixture 判别与 witnessed-equivalence 边界 |
| C adversarial corpus | `DRAFT_NOT_RUN` | 34 个设计 case；重叠切片由主 harness 运行，不冒充完整产品矩阵 |

本地 reference engine 是真实可执行的 policy worker，但不是 OPA/Cedar/OpenFGA/XACML 的
替身，也不支持关于这些产品的相对优劣。它的用途是验证 adapter 不预读
`ALLOW/REJECT/UNKNOWN/DEFER`：worker 只收到
[`fixtures/native-inputs.json`](./fixtures/native-inputs.json)，输出
`native_outcome/error/version/freshness`；独立 evaluator 在 stdout seal 之后才读取
[`fixtures/oracles/native-expected.json`](./fixtures/oracles/native-expected.json)，任务映射
再派生业务结果。未知 native 分支保留为 `UNMAPPED_NATIVE_OUTCOME` 或可解释
`UNKNOWN/DEFER`，不会默认变成 Allow。

## 目录

```text
fixtures/
  authority-worlds.json
  native-inputs.json
  provider-adapter-inputs.json
  materiality-standing-migration.json
  oracles/native-expected.json
  oracles/provider-adapter-expected.json
mcb_g5/
  common.py
  native_adapter.py
  simulation.py
workers/
  local_policy_engine.py
  owner_service.py
  target_service.py
tests/test_discriminator.py
research-a/A-owner-native-semantics.md
research-b/...
research-c/C-adversarial-findings.md
research-c/adversarial-corpus.json
runner.py
artifacts/results.json
artifacts/manifest.json
```

`owner_service.py` 是一个进程模板；runner 实际启动四个实例，每个实例生成并只使用自己的
store 与 Ed25519 private key。controller 只通过 JSON-lines API 读取和请求签名。因为这些
进程仍运行于同一 UID，这只构成 cooperative process separation，不抵抗能读取同一工作区的
恶意本机进程。

## 八项实现如何落地

1. **E1 crossed pair**：`U_TRUE_UNIFIED_AUTHORITY` 与
   `P_SAME_PERMISSION_EXTERNAL_RIGHT` 的技术权限、输入和工具相同，唯一差异是外部
   non-delegable right。permission-only center 在 P 中被判为 false allow；正确强中心查询
   外部 owner。另有 `X_SINGLE_DOMAIN_TX_EXTERNAL_EFFECT`，阻止把本地 ACID 记录当外部 Effect。
2. **Native outcome preservation**：policy worker 不含业务标签；adapter 保存原始结果、
   错误、policy version、input completeness、freshness、negative fact 和 resolver，再按
   `task-mapping-estuary-v1` 派生结果。另有 13 个四产品 native-shape adapter cases；
   它们明确是 synthetic shape fixture，不是产品运行返回。
3. **四 owner 独立**：四个进程、四个 store、四个 key，分别注入
   reject/revoke/outage/fork；其他 owner 状态必须不变。
4. **每个边界后的 race**：在 `read/re-read/sign/reserve/execute` 后注入 revoke；比较
   `NO_COMMON_TRANSACTION / BOUNDED_LEASE_CONFIRM / TWO_PC_LIKE_HOLD /
   SAGA_COMPENSATION / TRUE_UNIFIED_CENTER`。顺序重读不被称为跨域原子。
5. **Target fence**：target endpoint 自己持久化并比较 epoch。ignore、restart-loss 和
   cross-region reorder 都真实生成 stale Effect；只有 strict target 拒绝旧 token。
6. **Material closure**：共同绑定 canonicalization、sidecar、external dependency 和
   materiality rule。相同主 digest 仍可要求重新授权，不同 bytes 也可经 owner-approved
   canonicalization 判为语义等价。
7. **Standing lifecycle**：区分 registered/adjudicated、未预登记 late standing、冲突
   jurisdiction 和恶意阻塞 challenge；被驳回 challenge 不永久停止，保留 liveness floor。
8. **Migration**：faithful mapping 只声明
   `WITNESSED_EQUIVALENT_ON_THIS_CORPUS`，corpus 外保持 `UNKNOWN`；lossy mapping 因丢失
   native Unknown、forbid 或 provenance 被检出。

## Strong center 三层与公平赢家

| Stratum | 中心真正拥有的东西 | 正确边界 |
|---|---|---|
| U | 同一 Principal 合法拥有全部 required Authority，现实 effect 域接受中心写入，制度允许集中 | strong center 可直接胜出 |
| P | 技术账号/API/数据库权限与 U 完全相同，但外部 owner 保留 non-delegable right | 中心必须查询/等待 owner；不能用管理员写权限代签 |
| X | 中心只拥有本地记录的单域事务，外部 target 产生 Effect | 本地 ACID 最多提交 intent/outbox；需要 fence、readback、reconciliation |

成熟组合可以通过四个 owner receipt 完整闭合 P；CLM/HITL 与人类规则也可以在低频高后果
任务中以更低生命周期成本胜出。本 harness 没有真实 CLM 或真人，相关路线只是公平可达路径，
不是已运行赢家。

## 复现

依赖 Python 3 和本机已存在的 `cryptography`：

```bash
cd research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-011-g5-authority-conformance

PYTHONPYCACHEPREFIX=/tmp/mcb-g5-pyc \
  python3 -m unittest discover -s tests -v

PYTHONPYCACHEPREFIX=/tmp/mcb-g5-pyc \
  python3 runner.py --check
```

主要结果：

- [`artifacts/results.json`](./artifacts/results.json)：每个 run、raw native record、
  owner fault、race trace、target readback、migration declaration；
- [`artifacts/manifest.json`](./artifacts/manifest.json)：结果 raw/canonical hash、所有非
  runtime 源文件 hash 和真实 engine 状态。

runner 只清理并重建本目录的 `artifacts/runtime/current/`，不修改工作区其他位置。

## 当前结果与不能支持

当前内部 validation 全部通过。最有判别力的观察是：

- permission-only center 在 U 正确，在 P/X false allow；
- 无共同事务策略在 sign/reserve 后 revoke 时产生 transient stale Effect；
- bounded confirm 阻止这些 Effect；2PC-like hold 安全但阻塞；Saga 可收敛但曾产生需补偿
  Effect，不能写成原子；
- target 忽略 token、重启丢失 epoch 或 region 未同步时，ledger 正确仍会产生 stale Effect；
- faithful migration 只在已运行 corpus 上 witnessed-equivalent；lossy migration 被检出。

这些结果不能支持：

- canonical IR 或新协议必要性；
- OPA/Cedar/OpenFGA/XACML 产品质量或相对赢家；
- 四个本地进程等于四个现实 Principal/法律 Authority；
- 跨故障域线性一致性或拜占庭安全；
- 真人理解、真实 Standing 完备性、真实 Effect/Acceptance；
- corpus 外迁移等价或长期生产可靠性；
- 修改 X1/M01、NOW、PROGRAM、Problem、LineContract、MechanismProfile 或正式研究状态。

## 内部三路研究

- A 独立负责 owner/Authority/native semantics，形成
  [`research-a/A-owner-native-semantics.md`](./research-a/A-owner-native-semantics.md)；
- B 独立实现 race/fence 原型，形成
  [`research-b/README.md`](./research-b/README.md)、独立 owner simulator、runner、fixture
  与 10 个 tests；其结果不自动替代主 runner；
- C 独立攻击免费 registry、假原子、强中心不公平、Standing 与迁移，形成
  [`research-c/C-adversarial-findings.md`](./research-c/C-adversarial-findings.md) 和
  [`research-c/adversarial-corpus.json`](./research-c/adversarial-corpus.json)。

三路返回是不同认知责任，不是三份独立现实证据。最终结论以本 README、实际 runner、
tests 和 artifacts 的共同边界为准。
