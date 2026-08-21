# T6-G7-ORTHOGONAL-REPLAY-001

状态：`LOCAL_SYNTHETIC CANDIDATE / 18 WORLDS / 108 TRACES / NO FORMAL STATUS CHANGE`  
日期：2026-07-29

## 结论

这轮已经把 Wave 010 的“private truth 包装成 dependency API、共享 decision function、
硬编码 closure”替换成一条实际运行的本地链：

```text
public packet
→ native owner query
→ worker subprocess
→ intent persistence
→ commit-time fence
→ dispatch / response loss
→ target readback
→ independent Acceptance readback
→ local/global reopen
→ capsule export/import
→ old-runtime fencing
→ reconciliation
→ private grader
```

结果没有支持“G7 已解决”。六臂在 18 个 worlds 上共执行 108 条 trace：

- exact world pass：`23/108`；
- factual unsafe continuation：`5`；
- unjustified continuation：`17`；
- history rewrite：`0`；
- unreconciled-Effect worlds：`12`；
- missed reopen nodes：`132`；
- over-reopen nodes：`85`。

五个 factual unsafe 全部来自 public transcript 相同的 hidden-edge pair 中 revoked 分支
`w011`。五个独立 Authority 臂在没有新观察时选择继续；它们在 hidden-valid `w010` 保留
liveness，却无法区分 hidden-revoked `w011`。legitimately delegated center 在非委托
world fail closed，没有这五次提交，但只有 `w001` 属于其合法适用层，不能由此支持一般 T6。

当前最强候选仍是 mature composite：`11/18` exact world pass，`1` 次 factual unsafe，
`0` 次 unjustified continuation，T6 的 R2、R5、R7 通过；R1、R3、R4、R6、R8 失败。
这是一项有信息量的负结果，不是成熟组件胜出或新协议必要性的证明。

## 五态的降级

`CURRENT / REVOKED / UNKNOWN / REFUSED / STALE` 在本候选中只作为
`AuthorityObservationClass`，不作为完整控制态。private oracle 正交保存：

1. normative stance；
2. epistemic state；
3. refusal/choice；
4. channel outcome；
5. freshness/provenance；
6. fork/equivocation；
7. Effect phase；
8. coordinator epoch；
9. migration phase；
10. Acceptance applicability。

worker 只看到 provider-native response，例如 `{active:false, revision:43}`、timeout、两个
冲突的 native heads 或 Acceptance receipt。它看不到 normalized truth、hidden edge、
expected action、expected closure 或 T6 label。

## 权限域

实现将以下状态分别持有：

- owner service：native Authority response 与 commit-time policy；
- source runtime：source-local intent、history、timer、obligation 与 capsule exporter；
- target runtime：独立 importer、target-local history 与 continuation；
- effector：idempotency registry、commit fence、Effect store 与 authoritative readback；
- Acceptance owner：exact goal/effect/object decision；
- grader：full graph、hidden edge、orthogonal truth 与 expected closure。

`runner.py` 不 import 或打开 private oracle。六个 worker 是六个独立源文件和 subprocess，
没有共享 closure function；runner 会拒绝相同 source hash 的 method alias。

## 18 个高区分 worlds

| World | 主判别点 |
|---|---|
| `w001` | low-drift repeat control；同时是唯一明确合法委托层 |
| `w002` | explicit low-coupling revocation |
| `w003` | timeout，未持久化 intent、未 dispatch |
| `w004` | 同类 timeout，但 Effect commit unknown |
| `w005` | stale CURRENT / old head |
| `w006` | signed fork/equivocation |
| `w007` | refused disclosure |
| `w008` | refused action |
| `w009` | wrong-object Acceptance |
| `w010` | hidden edge current，public transcript 与 `w011` 相同 |
| `w011` | hidden edge revoked |
| `w012` | material goal/Acceptance change |
| `w013` | low-coupling optional leaf |
| `w014` | high-coupling shared root + partial Effect |
| `w015` | planned drain migration |
| `w016` | crash takeover + response loss |
| `w017` | old-runtime restart / split-brain |
| `w018` | capsule field drop |

world 数量固定为 18，没有扩到 1500。identifier permutation、truth-copy、method alias、
hidden-edge、history overwrite 和 capsule mutation 是攻击门，不作为新增 truth world。

## 六个方法臂

| Arm | 独立实现 | exact pass | factual unsafe | unjustified | T6 通过 |
|---|---:|---:|---:|---:|---|
| `B0` immutable contract + monitoring + human amendment | 是 | 3/18 | 1 | 5 | R2 |
| `B1` durable workflow/history/version/migration + human amendment | 是 | 3/18 | 1 | 4 | 无 |
| `MATURE` mature composite | 是 | 11/18 | 1 | 0 | R2, R5, R7 |
| `EQUAL_CENTER` equal-authority center | 是 | 2/18 | 1 | 4 | R2 |
| `DELEGATED_CENTER` legitimately delegated center | 是 | 1/1 applicable | 0 | 0 | `NOT_APPLICABLE` |
| `HUMAN` frozen human-rule institution | 是 | 3/18 | 1 | 4 | R2 |

`DELEGATED_CENTER` 只在 `w001` 的精确委托层有资格执行；其余 17 个 world 的 BLOCK 只是
不适用时的保守行为。grader 因而把它的 R1–R8 全部标为 `NOT_APPLICABLE`，避免 all-block
被误写成一般 T6 能力。

## T6 R1–R8

Mature composite 的当前结果：

| Requirement | 状态 | 当前边界 |
|---|---|---|
| R1 repeat 降本不增错 | `FAIL` | 记录了运行成本，但没有真实 cold-vs-repeat reformation 对照 |
| R2 offline 不等于规范失效 | `PASS` | `w003` no-dispatch 与 `w004` uncertain Effect 走了不同路径 |
| R3 撤销只影响依赖闭包 | `FAIL` | hidden revoked 仍误继续；局部 closure 也未全闭合 |
| R4 失效传播且不改历史 | `FAIL` | history 为 0 rewrite，但 unsafe/unreconciled world 未闭合 |
| R5 material goal change 回构成 | `PASS` | `w012` 进入 global reopen |
| R6 hidden dependency | `FAIL` | public-identical pair 上继续保 liveness，revoked 分支 unsafe |
| R7 高耦合诚实全局重开 | `PASS` | fork、goal root、shared root 均扩大重开 |
| R8 Context/history 可移植 | `FAIL` | `w004` readback 仍 timeout；`w018` field-drop 按预期 fail closed |

R8 的失败不等于 runner 没执行 migration：

- `w015` 实际 drain、advance epoch、export/import 后继续；
- `w016` crash takeover 对账 response-lost Effect；
- `w017` old runtime restart 的外部 response 再次丢失，但 effector ledger 证明旧 epoch
  `FENCED_OR_DENIED`，没有第二 Effect；
- `w018` 先保留 source Effect/Acceptance，再丢
  `compensation_obligations/acceptance_records`，target import 拒绝，mature 返回
  `BOUNDED_UNKNOWN`。

## 成本

每个 worker 在 PLAN、POST_MIGRATION、CLOSURE 三阶段返回自己的原生成本字段；完整原始值见
`results.json.by_method.*.cost`。当前成本维度并未标准化为同一货币或统一生命周期函数：

- B0：query、human minutes、governance；
- B1：query、human minutes、runtime；
- mature composite：query、human minutes、assurance；
- centers：query、human minutes、central ops；
- human rule：query、human minutes、handoffs、calendar wait。

因此本轮只保留成本轨迹，不宣布 lifecycle net-value winner。R1 也不会因“有 cost 字段”
被伪造为通过。

## 文件

- `fixture.json`：method-side fixture 和 provider scenarios；
- `private_oracle.json`：grader-only full graph 与正交 truth；
- `provider_simulators.py`：owner、effector、Acceptance、source/target runtime；
- `workers/*.py`：六个独立方法实现；
- `runner.py`：不读 oracle 的真实执行器；
- `private_oracle.py`：事后 grader 与攻击器；
- `run-traces.json`：108 条冻结原始 trace；
- `results.json`：逐 world、逐 method、逐 T6 requirement 结果与成本；
- `tests/test_attacks.py`：truth-copy、五态压缩、alias、capsule、history 攻击；
- `tests/test_runner.py`：实际 query/response-loss/migration/fencing 集成测试；
- `researcher-A.md`：原生 G7 五分面与实验合同重建；
- `manifest.json`：核心运行产物 SHA-256。

## 复现

在本目录运行：

```bash
PYTHONPYCACHEPREFIX=/tmp/g7-pycache \
  python3 runner.py --output run-traces.json

PYTHONPYCACHEPREFIX=/tmp/g7-pycache \
  python3 private_oracle.py run-traces.json --output results.json

PYTHONPYCACHEPREFIX=/tmp/g7-pycache \
  python3 -m unittest discover -s tests -v

PYTHONPYCACHEPREFIX=/tmp/g7-pycache \
  python3 -m py_compile runner.py provider_simulators.py private_oracle.py \
  workers/*.py tests/*.py
```

当前复核：`24/24 tests PASS`，18 worlds × 6 methods = 108 traces。

## 不能支持

本候选不能支持：

- 真人 Authority、现实 Effect、生产恢复或长期净值；
- mature composite 已完整解决 G7；
- delegated center 可外推到未委托独立 Authority；
- hidden private truth 可被 planner 猜出；
- cross-runtime 语义已经形成通用标准；
- 新协议必要或不必要；
- `NOW.md`、`PROGRAM.md`、LineContract、MechanismProfile 或正式 claim 的任何变化。

当前研究状态应保持：

```text
T6-G7-ORTHOGONAL-REPLAY-001 = LOCAL_SYNTHETIC_CANDIDATE
G7 INTEGRATED SOLUTION = NOT DEMONSTRATED
NOVEL PROTOCOL NECESSITY = NOT DEMONSTRATED
NEXT DISCRIMINATOR = add lawful hidden-edge observation or accept explicit safety-liveness policy,
                     then run real cold-vs-repeat and a second independent base family
```
