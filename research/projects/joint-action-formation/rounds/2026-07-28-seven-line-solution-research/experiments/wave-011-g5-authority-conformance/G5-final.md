# 第二批 Codex CLI G5-final

日期：2026-07-29  
cohort：`codex-cli-cohort-002`  
状态：`MCB-G5-v2 LOCAL SYNTHETIC DISCRIMINATOR COMPLETE / NO FORMAL PROMOTION`

## 核心结论

本 cohort 没有发现一个已经稳定、必须由新 G5 协议或 canonical IR 解决的 residual。

更精确的结果是：

1. Wave009 的 B0/B5 `24/24` 仍只支持有限结构化本地模型中的成熟组合正例；
2. M01 仍是 scoreable-pair freeze candidate，不是四个现实 Authority owner 已闭合；
3. MCB-G5-v2 已把审计提出的 owner、native outcome、race、fence、material closure、
   Standing 和 migration 候选断点变成可运行小型 discriminator；
4. discriminator 成功暴露了 permission-only center、免费 registry、顺序重读假原子、
   无 target enforcement 的 fence、主 digest 假闭包和 migration 假等价；
5. 这些失败目前都能由更诚实的 Authority-aware center、owner receipt、bounded confirm、
   owner hold、target fence、material closure、Standing lifecycle 或薄 task adapter
   区分，尚没有重复到需要新通用协议；
6. 强中心、成熟组合、CLM/HITL 和人类规则完整解决都保留为正结果。特别是强中心在真正统一
   Authority 的 U 世界直接胜出，不构成研究失败。

因此本轮最强裁决是：

```text
NO_CANONICAL_IR_JUSTIFIED
NO_STABLE_G5_RESIDUAL_ESTABLISHED
MCB_G5_V2_DISCRIMINATOR_IMPLEMENTED
MATURE_AND_HUMAN_SOLUTIONS_REMAIN_FULL_POSITIVE_PATHS
```

## 三名内部研究者实际返回

本 CLI 实际并行启动了三名内部研究者，没有模拟：

- A：owner / Authority / native semantics，交付
  [`research-a/A-owner-native-semantics.md`](./research-a/A-owner-native-semantics.md)；
- B：race / fence / conformance simulator，交付
  [`research-b/README.md`](./research-b/README.md)、独立 subprocess owner 实现、runner、
  fixture 和 10 个 tests；
- C：免费 registry、跨 Authority 假原子、迁移损失和强中心不公平攻击，交付
  [`research-c/C-adversarial-findings.md`](./research-c/C-adversarial-findings.md) 与
  34-case [`research-c/adversarial-corpus.json`](./research-c/adversarial-corpus.json)。

A/B/C 是不同认知和实现责任，不是三个独立现实机构，也不把模型共识当证据。主线程另行综合、
实现并运行了本目录的最终 runner。

## 实际实现与观察

### 1. U/P/X strong-center strata

[`fixtures/authority-worlds.json`](./fixtures/authority-worlds.json) 冻结三个 stratum：

- `U_TRUE_UNIFIED_AUTHORITY`：中心 Principal 合法拥有全部 required Authority，现实 effect
  域接受中心写入，制度允许集中；
- `P_SAME_PERMISSION_EXTERNAL_RIGHT`：技术账号、API、数据库权限与 U 完全相同，唯一差异是
  site-data owner 保留 non-delegable right；
- `X_SINGLE_DOMAIN_TX_EXTERNAL_EFFECT`：中心只拥有本地记录，外部 target 产生 Effect。

实际 runner 的 permission-only center 在 U 中正确 Allow，在 P/X 中均被判 false allow。
Authority-aware strong center 在 P 中查询外部 owner，在 X 中转入
outbox/fence/target-readback。成熟组合、CLM/HITL 和人类规则都可在取得 exact owner
receipt 后前进。

这一区分说明：管理员能写 `approved=true` 只证明技术能力，不证明 Authority 所有权。

### 2. Native outcome preservation

[`workers/local_policy_engine.py`](./workers/local_policy_engine.py) 作为真实本地 subprocess
engine 实际运行 7 个 case。worker 输入不包含业务四值 oracle，只输出：

```text
native_engine
native_outcome
native_error
policy_version
input_complete
source_freshness
negative_authority_fact
resolver
```

stdout 被 hash 后，task adapter 才按版本化 mapping 派生业务结果；独立 evaluator 最后读取
oracle。7 个 native outcome 和 7 个业务 mapping 均 exact。

另有 13 个 OPA/Cedar/OpenFGA/XACML native-shape adapter cases，全部通过薄 adapter
conformance；它们明确是 synthetic native-shape fixture。机器上没有相应 CLI，Docker
socket 也不可访问，所以四个产品均为：

```text
OPA      NOT_RUN_ENGINE_NOT_INSTALLED
CEDAR    NOT_RUN_ENGINE_NOT_INSTALLED
OPENFGA  NOT_RUN_ENGINE_NOT_INSTALLED
XACML    NOT_RUN_ENGINE_NOT_INSTALLED
```

这不是产品比较，不能用 13 个 shape cases 宣称任何产品已接入。

### 3. 四个 owner 独立 process/store/key

主 runner 实际启动：

```text
program-coordinator
delta-calibration
independent-validation
site-data-steward
```

四者拥有四个不同 PID、store 和 Ed25519 public/private key。controller 只走 JSON-lines
接口。定向 fault 分别观察到：

- program owner 独立 `REJECT`；
- delta owner 独立 `REVOKE`；
- validation owner 独立 `OUTAGE`；
- data steward 独立签发 forked heads；
- 每次 mutation 后其他三个 owner 的 state 不变。

这是 cooperative same-UID process separation，不抵抗能读取同一工作区的恶意本机进程，
也不是真实组织或法律 Authority。

### 4. 每个边界后的 cross-owner race

主 runner 对五种策略、U/P 两种 Authority topology 和五个注入边界运行 50 个 cells：

```text
read → re-read → sign → reserve → execute
```

每个边界后都能注入 revoke。当前有限矩阵观察为：

| 策略 | cells | transient stale Effect | safe final | 阻塞/持锁 |
|---|---:|---:|---:|---:|
| no common transaction | 10 | 4 | 6 | 0 |
| bounded lease + confirm | 10 | 0 | 10 | 0 |
| 2PC-like owner hold | 10 | 0 | 10 | 10 |
| Saga + compensation | 10 | 4 | 10 | 0 |
| true unified center / P 中 not-applicable | 10 | 0 | 10 | 0 |

所以：

- 顺序 read/re-read/sign 不是跨 Authority 原子；
- bounded confirm 在当前 revoke placement 下阻止 stale Effect，但不证明 simultaneous
  snapshot 或现实 owner 会提供 lease；
- 2PC-like hold 的安全来自 owner 明确 hold，同时留下阻塞成本；
- Saga 的 final convergence 不删除 4 个已发生的 transient Effect，不能写成原子；
- P 中 unified center 被判为 `NOT_APPLICABLE_EXTERNAL_NON_DELEGABLE_RIGHT`。

B 的独立实现以另一套代码又通过 10 个 tests，复现相同保证边界；它仍是同一工作区和本地
synthetic evidence。

### 5. Target-side monotonic fence

target worker 不是检查 ledger 是否发 token，而是让旧 executor 的 token `1` 在新 epoch `2`
后真实抵达 target：

| target profile | 结果 |
|---|---|
| strict persistent monotonic comparison | `STALE_FENCE_REJECTED` |
| ignore token | stale Effect |
| restart loses highest epoch | stale Effect |
| cross-region local reorder | stale Effect |

因此 fencing 的保证属于真实 side-effect endpoint；ledger、workflow variable 或 token 字段
本身不构成 enforcement。

### 6. Material closure、Standing 与 migration

Material operation closure 实际区分：

- 相同 primary digest、material sidecar 改变；
- 不同 bytes、owner-approved canonicalization 后等价；
- 相同主对象、external dependency head 改变；
- materiality rule version 未知。

Standing fixture 覆盖 registered suspensive challenge、未预登记 late stakeholder、冲突
jurisdiction 和恶意阻塞 challenge。被驳回 challenge 可以继续，保留 liveness floor；
late stakeholder 进入 reopen/compensation，不能靠预注册 case schema 宣称主体全集完整。

Migration 的 faithful mapping 只得到：

```text
WITNESSED_EQUIVALENT_ON_THIS_CORPUS
outside_corpus = UNKNOWN
```

lossy mapping 因丢失 native Unknown、forbid 或 owner/source provenance 被检出。没有声明
OPA、Cedar、OpenFGA、XACML 或 CLM 之间的一般逻辑等价。

## 对 C 攻击语料的处置

C 的 34 cases 覆盖 7 个 attack family：

```text
REGISTRY
AUTHORITY_STRATUM
RACE
MATERIAL_OPERATION_CLOSURE
TARGET_FENCE
STANDING
MIGRATION
```

主 runner 机械确认 ID 唯一、七族齐全、五个 race boundary 齐全。与主夹具重叠的 owner、
race、fence、materiality、Standing、migration 切片已实际运行；完整 34-case 跨产品矩阵仍为
`DRAFT_NOT_RUN`。特别是 delayed publication、backdated revocation、key compromise 和真实
异构产品 holdout 仍不能写成已跑结果。

C 最强的两个反例被保留：

1. U/P 技术权限完全相同，仅 external non-delegable right 不同；同判 Allow 就是
   Authority substitution；
2. 所有 read/re-read/sign/reserve 曾经正确，但最后检查后 revoke，且 target
   ignore/restart-loss/region reorder；局部全绿仍能产生 stale Effect。

## 交付

本 cohort 只在
`experiments/wave-011-g5-authority-conformance/` 写入：

- [`README.md`](./README.md)：范围、架构、复现和完整限制；
- `fixtures/`：U/P/X、native、provider adapter、materiality、Standing、migration；
- `workers/`：local policy engine、owner service、target service；
- `mcb_g5/`：adapter、signature/readback、race/fence/migration orchestration；
- [`runner.py`](./runner.py)；
- [`tests/test_discriminator.py`](./tests/test_discriminator.py)；
- `research-a/`、`research-b/`、`research-c/` 三路原始返回；
- [`artifacts/results.json`](./artifacts/results.json) 与
  [`artifacts/manifest.json`](./artifacts/manifest.json)；
- 本文件。

没有修改 `research/NOW.md`、`PROGRAM.md`、Problem、LineContract、MechanismProfile 或正式
研究状态。

## 验证

主实现：

```text
6/6 unittest PASS
runner.py --check PASS
50 race cells RUN
7 local native-engine cases exact
13 provider native-shape adapter cases exact, products NOT_RUN
4 owner process/store/key distinct
10 internal validations PASS
```

B 独立原型：

```text
10/10 unittest PASS
```

JSON 全部可解析，Python compileall 通过，交付路径之外的既有工作区改动未被回滚或覆盖。

## 证据边界与下一行动

本轮只支持“这些候选失败可被一个小型本地 discriminator 区分”。它不支持：

- canonical IR；
- 新 Authority 协议必要性；
- OPA/Cedar/OpenFGA/XACML 产品比较；
- 四个本地进程等于四个现实 Principal；
- 跨故障域线性一致性；
- 真实 CLM/HITL/人类成本赢家；
- 真人授权、法律充分性、真实 Effect/Acceptance；
- corpus 外 migration equivalence；
- M01/X1 已进入 scoreable population。

下一条最高信息增益不是扩大 ontology，而是选择一个实际可安装的成熟 engine（优先 OPA 或
Cedar）替换 synthetic native shape，保持相同 raw-outcome oracle 隔离；随后在一个低风险、
可撤销、四 owner-facing decision 的任务中运行 U/P pair。若成熟组合完整闭合，residual
保持零；只有相同断点跨两个异质任务、未见 holdout 和两个独立实现复现，且强中心、成熟组合、
CLM/HITL、人类规则和合理 adapter 都失败，才重开新机制候选。
