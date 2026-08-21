# Wave 008 G3 QHM-1 causal replayer

状态：`LOCAL_FINITE_SYNTHETIC_TRUSTED_PARENT_SELF_TEST_ONLY`

这是旧 `wave-008-g3-discriminator` 的因果判别重构，不修改旧实验。目标不是证明一个新机制，
而是在冻结、有限、可穷举的 Qualified Handoff MiniSim 中，区分：

- 旧模型已有 direct path；
- 旧模型内的 ordinary preparation prefix；
- operative enabling condition 是否是既存条件激活或新 token；
- action kernel / policy 是否发生物质变化；
- task 是否保持不变；
- surface success 是否通过 authority、target、acceptance 与 cost verifier；
- action inventory 不完备时为什么只能返回 `UNKNOWN`。

外部模型、网络和第三方调用均为 `0`。

## 冻结对象

`qhm1/spec.py` 是本实验的可执行冻结入口，绑定：

- immutable old task `QHM1-OLD-TASK-v1`；
- L0 direct、L1 preparation、L2 model/institution action alphabet；
- authority map；
- 每个 hidden world 的 scripted principal policies；
- horizon `10`、cost budget `10`、privacy budget `2`、human quota `1`；
- target artifact/schema、exact-once、necessary principals、acceptance 和 value floor。

`frozen_package(world)` 分别计算 task、action model、authority map、principal policies、
resource account 及整个 package 的 SHA-256。SAT witness 与 UNSAT certificate 都绑定实际
action model fingerprint；checker 另将 `initial_state / transition / route_ready /
abstract_qualified / encoding / resource package / checker version` 绑定为
`executable_model_fingerprint`。同步改文字标签或 transition 实现不能保留同一证书。

可执行 old `Q` 由五个分离 verifier 合取：

1. `AuthorityVerifier`：holder、task、payload、receipt 与 actor；
2. `TargetVerifier`：target store 中 exact artifact / schema / exact-once / readback；
3. `AcceptanceVerifier`：T holder 的 acceptance receipt；
4. `CostVerifier`：parent-owned ledger、horizon、cost、privacy、human quota 与 trace
   exact match；
5. `InformationVerifier`：parent-owned `InspectionRecord`、实际返回内容 hash、task、
   trial、义务、ledger index，以及 planner 实际观察 hash 的逐项一致性。

Candidate 的 success label 不进入 `Q`。

## Holder 执行边界

系统只能调用公共 gateway 请求 action，不能传入 actor。每个 privileged action 由
`PrincipalHolder` 构造时固定自己的 scripted policy 与 authoritative effect capability；
公共 `dispatch()` 只接受冻结 action request，不再接受调用者提供的 policy/effect callback。
Holder 执行 effect 后，receipt 签名覆盖 canonical receipt id、payload/task、effect-log id、
before/after state digest 和 success。Evaluator 再从 bundle 外的 parent evidence anchor
核对 canonical inspection、effect log 与完整 bundle seal。Controller `C` 不能自签成
O/P/T/H/A/W。`H` holder 的 adapter build 同时真实消耗冻结 human quota。

这是“真实 holder 对象执行”的本地合成边界，不是：

- 独立 OS principal；
- 不同 UID、container 或 remote authority；
- hostile same-filesystem containment；
- 恶意 native code 安全保证。

输出只保留 receipt binding 与验证结果，不保存随机 secret。

## Blinded worlds

三个系统只看到 deterministic opaque trial id、paired initial message 和 `INSPECT` 返回，不导入
hidden-world module。runner 在 trial seal 后才合并 truth id。该 blinding 是接口隔离，不是
对同权限恶意 Python 代码的 sandbox。

| World | L0 | L1 | L2 | 声明层深度 | 因果含义 |
|---|---|---|---|---:|---|
| discover | SAT | SAT | SAT | 0 | 已有未广告 alternate route |
| enable | UNSAT | SAT | SAT | 1 | 既存 endpoint 被 holder 激活 |
| commit | UNSAT | SAT | SAT | 1 | prefix closure SAT，同时 O 首次签发 operative authorization token |
| build-known | UNSAT | SAT | SAT | 1 | 旧 build/install action 构造 adapter |
| extend | UNSAT | UNSAT | SAT | 2 | 当前表示中需 propose/register operator |
| combo | UNSAT | SAT | SAT | 1 | 授权、route、known adapter 三个阻塞同时存在 |
| drift | UNSAT | UNSAT | UNSAT | — | old-task value floor 已失败；本 world 只证明正确停止，不执行改题攻击 |
| substitute | UNSAT | UNSAT | UNSAT | — | owner 明确拒绝；本 world 只证明正确停止，不执行 controller 替代攻击 |
| unsat | UNSAT | UNSAT | UNSAT | — | 完备有限 inventory 内没有 qualified path |
| open-invent | UNKNOWN | UNKNOWN | UNKNOWN | — | inventory 明确不完备，禁止伪造 UNSAT certificate |

所有 UNSAT 都来自穷举 frontier exhaustion，不是 planner timeout 或 world label。
`open-invent` 也穷举当前 declared edges，但因为 inventory 不完备，只输出
`UNRESOLVED_MODEL`，不生成 UNSAT certificate。

这里的 closure oracle 量词是：**每个给定 world 内，是否存在一条有限 action sequence**。
它不是 observation-contingent policy synthesis，也不证明同一策略在所有允许的 Principal
response family 中稳健。运行时三个 planner 是看完本实验一次精确 `INSPECT` 后的确定性
actual policy；robust reachability 明确为 `NOT_TESTED`。

## 三个能力完全对齐的系统

- `same_information_strong_center_hitl`
- `mature_workflow_composition`
- `formation_candidate`

三者具有逐 action 相同的观察、holder endpoints、human access、L2 channel、budget、
horizon 和 verifier。三者的 policy 方法分别实现为 backward-chaining center、固定
exception-routing workflow 和 intervention-set candidate；报告绑定三个不同的 policy
source fingerprint。`combo` world 强制三个 policy 产生三种不同但都合法的 preparation
顺序，使“不同实现”不只停留在源码拼写；共享 gateway/execution loop 不计作策略差异。
三者仍由同一代码库和同一研究流实现，独立实现状态明确为 `NOT_ESTABLISHED`。

本 fixture 的确定性结果：

- `18 QUALIFIED_SUCCESS`：6 个可解 world × 3 个系统；
- `9 BOUNDED_UNREACHABLE`：drift/substitute/unsat × 3；
- `3 UNRESOLVED_MODEL`：open-invent × 3；
- formation candidate 独有成功：`0`；
- strong center 与 mature workflow 都完整覆盖本 fixture 的 bounded cases。

这是三个同研究流**合成 scheduling variants**在本 fixture 中完整覆盖的正向结果，不是
“通爻价值为零”，也不是 novelty penalty。三者的 blocker taxonomy、动作映射、停止条件
和执行器仍共享；当前差异只足以证明不同 preparation ordering 下的同覆盖，不足以冒充
真实成熟产品、真人 workflow、生产 HITL 或独立 formation 方法已经被比较。

输出 disposition 允许并实际保留：
`none-needed / central / human / adapter / combined / new / Unknown`。

## C/N/E/T/V 正交向量

每个 qualified run 输出：

- `C` closure：`SAT / UNSAT / UNKNOWN`；
- `N` operative enabling delta：`NONE / EXTANT_ACTIVATED / NEW_TOKEN`；
- `E` kernel/policy delta：`SAME / CHANGED / UNKNOWN`；
- `T` task：`INVARIANT / DRIFTED / UNKNOWN`；
- `V` validity：`VALID / INVALID / NO_QUALIFIED_EFFECT`。

Layer depth 仍保留为冻结实验表示中的计算结果，但所有输出标明
`DECLARED_EXPERIMENT_LAYER_ONLY_NOT_ONTOLOGY`。

四个承重 gate：

1. `TOKEN-COMMIT`：三个系统均计算出 `C=SAT, N=NEW_TOKEN, E=SAME,
   T=INVARIANT, V=VALID`，新 token 由固定 O-holder policy、receipt、effect log 与
   parent evidence anchor 共同约束。这直接保留
   “prefix closure SAT 与 condition formation 可同时成立”。
2. `META-REFACTOR`：同一 `extend` 物质 transition 分别编码为
   `register_new_operator` 和 `install(spec)`；终态 digest 与 N/E/T/V 相同，
   depth 从 `2` 变为 `1`。因此 depth 不是 ontology。
3. `KNOWLEDGE-PROVENANCE`：knowledge-only replay 重置 S0 时消费 parent-owned
   `InspectionRecord` 中的实际 observation，只由 observation-aware L0 policy 规划；
   source、response hash、parent ledger cost、privacy cost 与 task-bound obligations
   均进入验证；不一致注入、丢失义务、planner 看到未绑定返回，以及同步改写 bundle 内
   facts/trace/ledger/hash 都必须被 bundle 外 parent anchor 拒绝。
4. `OPEN-INVENT`：inventory 不完备时 `C=UNKNOWN / UNRESOLVED_MODEL`，没有伪 UNSAT。

## 每个 success 的自动重放

所有 18 个 qualified success 都运行：

- knowledge-only：exact S0 + 合法取得的信息、provenance/privacy/obligation/cost；
- fixed-model-prefix：L0+L1 exhaustive closure；
- exact model-diff：只施加本次 L2 diff 后重新跑 L0；
- immutable old-task verifier；
- 每个 privileged receipt 的 controller authority substitution；
- duplicate target effect；
- authoritative cost-entry deletion；
- 所有 L1/L2 intervention subset 的穷举 ablation 与 minimal sufficient set。

这些重放分别计算，不从 `discover/enable/...` truth label直接映射结果。

## 复现

在本目录运行：

```bash
PYTHONPYCACHEPREFIX=/tmp/qhm1-test-cache \
  python3 -m unittest discover -s tests -v

PYTHONPYCACHEPREFIX=/tmp/qhm1-run-cache \
  python3 -m qhm1
```

输出：

- `outputs/report.json`：完整 matrix、replay、向量和 comparative result；
- `outputs/model-check.json`：每个 world 的 L0/L1/L2 witness/certificate；
- `outputs/theory-gates.json`：四个承重 gate；
- `outputs/traces.jsonl`：holder-executed traces 与 receipt verification。

## 证据边界

本实验支持的最强陈述是：

> 在这套冻结的有限合成状态与 scripted policy 中，穷举器和 runtime verifier 能区分
> 旧闭包、operative token 变化、kernel/policy 变化、task invariance 与 invalid success；
> 三个同研究流、本地合成 scheduling variants 在能力对齐后覆盖相同 bounded cases；
> 中心与 workflow 形态的合成覆盖是正向结果。

它不能支持：

- 真实 Principal 的理解、同意、承诺、采纳或责任；
- absolute real-world unreachability；
- open-ended invention、未知 action inventory 或开放世界的 UNSAT；
- robust reachability across every allowed principal response family；
- hostile-code containment、生产安全、长期 exactly-once 或跨节点 ledger；
- 商业价值、现实频率、迁移性、可扩展性；
- 新 formation method、A2A、联邦或通爻的必要性/独特性；
- 该分类是本体论，或同研究者 local self-test 是独立复核。

失败与修复历史保存在 `FAILURE_HISTORY.md`。
