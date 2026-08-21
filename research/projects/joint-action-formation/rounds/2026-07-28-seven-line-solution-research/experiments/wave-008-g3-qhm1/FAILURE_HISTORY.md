# QHM-1 failure history

本文件保留实现过程中的真实红灯，不把最终绿灯倒写成一次成功。

## 1. 测试先行的首次失败

命令：

```bash
PYTHONPYCACHEPREFIX=/tmp/qhm1-first-red \
  python3 -m unittest discover -s tests -v
```

首次结果：

```text
ModuleNotFoundError: No module named 'qhm1'
Ran 1 test
FAILED (errors=1)
```

原因：先落下完整行为契约测试，`qhm1` package 尚未实现。

修复：新增冻结 spec、hidden worlds、checker、holder runtime、三个系统、replayer 与 runner。

## 2. 首版实现无法冻结 action tuple

结果：10 项测试中 8 项 error。

首个共同错误：

```text
TypeError: Object of type ActionSpec is not JSON serializable
```

原因：canonical serializer 只处理顶层 dataclass，没有递归处理 tuple 中的 `ActionSpec`，
导致 action model fingerprint 无法计算。

修复：canonical JSON 增加 dataclass-aware `default`，嵌套 action specs 进入实际 fingerprint。

## 3. build/extend 被错误判成 unreachable

结果：

```text
expected build-known depth 1, observed None
QUALIFIED_SUCCESS 9, UNRESOLVED_MODEL 6
```

原因：`SCHEMA_BLOCKED` 被错误初始化成 endpoint disabled。真实冻结语义是 endpoint 已启用，
但 schema 不兼容；这把 schema repair 和 endpoint activation 混成同一变量。

修复：`SCHEMA_BLOCKED` 初始化为 endpoint enabled，仅由 adapter install 或 operator register
改变 schema readiness。修复后 10/10 测试通过。

## 4. OPEN-INVENT 增量后的旧计数断言失败

结果：12 项中的两项旧断言失败，仍期待 8 worlds / 24 runs。

原因：加入 action inventory 不完备的第九个 world 后，测试分母尚未同步。

修复：分母改为 9 worlds / 27 runs，并新增独立断言：所有 layer 均
`unresolved_reason != null`、`unsat_certificate == null`，三个系统输出
`UNRESOLVED_MODEL`。

## 5. 三个系统曾共用同一个策略实现

首次实现中，Strong Center、Mature Workflow 与 Formation Candidate 只有标签不同，
都继承 `BaseSystem.run` 中的同一套规划逻辑。即使三者成功集相同，也不能据此形成
“不同现有组合与候选方法能力相同”的比较结论。

修复：三个系统分别实现 backward chaining、固定规则图和 blocker/intervention loop；
报告冻结三个 `plan` 的源码指纹，并要求它们互不相同。共享部分只保留相同诊断接口、
执行器、authority holder 和 verifier，以维持公平执行条件。

## 6. 测试通过但报告入口读取旧字段

策略独立化后，报告字段从
`existing_compositions_close_all_bounded_worlds` 改为
`synthetic_existing_compositions_close_all_bounded_worlds`，但命令入口仍读取旧字段。

结果：

```text
KeyError: 'existing_compositions_close_all_bounded_worlds'
```

修复：同步入口字段，并把命令执行加入本轮实际验证；这也说明 12 项单元测试此前没有覆盖
最终用户入口。

## 7. Knowledge gate 曾把结论写成常量

首版 `knowledge_only` replay 中，`obligations_preserved` 和
`free_information_injection_used` 是作者直接写入的常量，不能证明来源、隐私成本和用途
义务真的进入状态与验收。

修复：`INSPECT` transition 现在生成 provenance/obligation state；closure 与最终 evaluator
都要求该绑定成立。自动重放另外构造“已知信息为真、但无来源、无成本、无义务”的伪状态，
要求 model checker 不得给出 qualified witness，且 runtime verifier 必须返回
`INFORMATION_PROVENANCE_OR_OBLIGATION_INVALID`。

独立攻击随后指出，只有两个 provenance boolean 仍不等于 knowledge 被实际消费；首版 replay
依旧把完整 hidden world 交给 omniscient BFS。第二次修复新增 parent-owned
`InspectionRecord`，绑定 response 内容、task、trial、义务和 ledger index；planner 实际
观察 hash 必须一致。knowledge-only replay 改为只从该 observation 生成 L0 plan，不再用
hidden world 搜索 plan。

## 8. 空策略也能让比较器真值为真

独立 mutation 把三个 planner 都改成永远停止后，三个 success set 同为空集，旧比较器仍因
“三个集合相等”返回 true；`all([])` 也让 Knowledge gate 空集通过。

修复：比较器现在要求每个系统的 success/unreachable 集精确等于 bounded oracle 的
SAT/UNSAT 集，且 SAT 集非空；Knowledge gate 也要求至少一个实际 success。新增 all-stop
mutation 回归，要求所有正向比较字段变 false。

## 9. 源码不同不等于策略不同

三个 `plan` 有不同源码指纹，但在九个单阻塞 world 上逐 action trace 完全相同。

修复：新增同时具有 authorization、route、known-adapter 三个独立阻塞的 `combo` world；
backward chain、固定 workflow 与 intervention set 产生三种不同的合法 preparation 顺序，
但在相同 verifier 下都完成 old task。报告同时绑定 behavior signature，并明确三者仍来自
同一代码库和同一 authoring stream，不构成独立实现证据。

## 10. 结果包曾携带自己的验签根

首版 `VerificationBundle` 包含 registry，evaluator 直接调用该对象验签；非 authorization
receipt 也没有把 payload hash 与冻结任务的期望 payload 逐项比对。

第一步修复：trusted registry 由 parent runner 单独传入 evaluator，不再进入 claimant
bundle；每个 action 的 exact payload、task fingerprint、holder、receipt 唯一性和签名
都需通过。错误 payload 现在由 holder 在签发前直接拒绝。

## 11. Holder 曾签署调用者提供的 policy 与 no-op effect

独立复测发现 `dispatch(request, policy_allows, effect)` 仍允许调用者把拒绝 world 改成允许，
或让 holder 对 no-op effect 签 receipt。Receipt ID 没进入 HMAC；TargetRecord 也没有核对
PROJECT receipt 引用。

修复：holder 构造时固定 policy/effect capability，公共 dispatch 只接受 request；receipt
签名覆盖 canonical ID、effect-log、before/after state digest 与 success。Evaluator 从
bundle 外的 trusted effect store 和 bundle seal 复核因果链。新增 policy-refusal、
callback-injection、receipt rename 和 broken project-receipt mutation。

## 12. 三份一致记录仍可被同步改写

`InspectionRecord`、trace 和 ledger 都在 claimant bundle 内；同步改 facts/hash 与 evaluator
收到的 observed hash，旧 verifier 仍会认为 information valid。

修复：parent runner 另持 canonical inspection records 与完整 bundle fingerprint，不进入
claimant bundle。同步改写 facts、trace、ledger 和 observed hash 后，
`information_valid=false` 且 `PARENT_EVIDENCE_SEAL_INVALID`。

该 seal 的威胁边界仍是受信 parent 与 gateway 隔离；它不抵抗能够改写 parent runtime、
Python 进程内存或本地源代码的恶意同权限代码。

## 13. UNSAT certificate 曾不绑定 transition 实现

只把 `ACTION_SPECS` 作为 action-model fingerprint 时，把 checker 使用的 `transition`
改成永远返回 `None`，可以让 discover 从 SAT 变成 UNSAT，同时 certificate fingerprint
保持不变。

修复：新增 executable-model fingerprint，绑定 initial state、transition、route readiness、
qualified predicate、encoding、resource package 与 checker version。Kernel-mutation 回归
现在要求结论改变时 executable fingerprint 必须改变。

## 当前本地状态

```text
Ran 15 tests
OK
```

该绿灯和报告生成仅表示同研究者在本地合成 fixture 中完成回归，不构成
blind independent audit。
