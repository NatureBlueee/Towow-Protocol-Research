# Wave 023 独立准入审计

日期：2026-08-01  
审计角色：独立 acceptance reviewer  
状态：`DEVELOPMENT MANIFEST ADMISSION ACCEPTED / ACTUAL COMPARISON ADMISSION REJECTED`

## 结论

当前实现可以接受一个封闭外层结构、可重算哈希、明确不执行也不计分的开发 fixture；它不能
准入实际比较，也没有产生任何 treatment、任务、能力、成本或赢家结果。

机器返回的最高状态为：

```text
DEVELOPMENT_SMOKE_ADMISSION_ACCEPTED_UNSCORED_NOT_EXECUTED
comparison_status = NOT_RUN
comparative_evidence = NONE
winner = NOT_EVALUATED
```

独立审计允许的完整表述最多是：

```text
WAVE023_DEVELOPMENT_MANIFEST_ADMISSION_ACCEPTED_UNSCORED_NOT_EXECUTED
SELECTED_ATTACK_SURFACES_CLOSED
ACTUAL_COMPARISON_ADMISSION_BLOCKED
NO_TREATMENT_OR_CAPABILITY_RESULT
NO_COMPARATIVE_EVIDENCE
NO_WINNER
```

这里的 `accepted` 只表示开发 manifest 与本轮已实现的静态门一致。它不表示 candidate 已被
启动、controller receipt 来自真实进程、Authority 合法、failure 实际发生、预算已在运行中
计量、Effect 或 Acceptance 存在，也不表示公平比较已经开始。

## 本次实际审计对象

| 对象 | 文件 SHA-256 | 内部 seal |
|---|---|---|
| `RUN-CONTRACT.json` | `05d6156b12913962805fd3d3ce6a4363a8fe6fe8cf2e2f241e374559c7d22524` | `0a6313ae6ec835be6c044dd75cf546db3d63d31f988782962065baaae531f627` |
| `fixtures/FAIR-SEALED-BATCH.json` | `329dfd99776086441f93f551901163d80374ebb5eb1d184b1f109da33b8b5f27` | `b8e59eaf87dc64d0e8e32f3c1ea4faf91674cf503e5b7361755f95cd36708620` |
| `admission_validator.py` | `9f7864e6be4f7563fafacde49f72ad1de001709894f289aaa7d25526dd5c73ae` | 不适用 |
| `tests/test_admission_contract.py` | `d041b2bc5697d3596f1a2c57d99cf4753484d863acb756b08c29ddf528138134` | 不适用 |
| `README.md` | `432bcec81f207e1c66851893f935e55d367ffe8a5870d287f8262d3e1e83cbbf` | 不适用 |

本审计只新增本文件，没有修改 contract、validator、fixture 或 tests。

## 独立复验

定向测试结果：

```text
38 passed in 0.35s
```

测试仅证明其实际断言覆盖的准入性质；通过数量本身不构成运行、比较或现实结果。

独立 reviewer 另外直接构造并重新计算所有相关 receipt 与 batch self-hash，而不是依赖陈旧
哈希使攻击失败。结果如下：

| 重放攻击 | 独立结果 | 实际拒绝原因 |
|---|---|---|
| A3 candidate 写入 `semantic_case_id`、expected disposition、private truth 与 oracle runtime | `REJECT` | sealed candidate bytes 命中禁止的 case/oracle marker |
| A3 meter log 写入 10,000 model calls、hidden retrieval 和巨量 token，同时继续自报零 | `REJECT` | closed meter schema 拒绝未知字段，observed 还必须由 ledger 独立汇总 |
| A4 trigger 改为 `AFTER_GRADER_SUCCESS / POSTHOC_ONLY_IF_SUCCESS` | `REJECT` | event class 与 intervention 不在预注册 allowlist |
| 把同一 fixture 改报 `ACTUAL_COMPARISON_SEALED_NOT_RUN`、live controller、两次 replicate | `REJECT` | trusted controller、Authority、meter、replicate 与 root seals 未实现，actual mode 硬拒绝 |

另外，独立 reviewer 把完整 Q 分别改成“至少一次”、允许 preflight 缓存 Authority、允许
controller PASS 代替 owner-native Acceptance，并重算 Q 与 contract self-hash；三项均因偏离固定
Q preimage 而被拒绝。Problem v1/v2 的机器与人类快照也都按固定文件哈希重新读取。

## 已关闭的门

在上述文件版本与开发 fixture 作用域内，以下门有直接机器证据：

1. Wave 021 文件字节、其内部 contract hash 与八项 source binding 会被重算；Problem v1/v2
   的四份快照也被精确绑定。
2. Q 不是可由本轮 contract 作者任意替换的长文本；exact Q hash、对象、Target、operation、
   时限、功率、安全、噪声、O_Q/O_V Acceptance 与 O_P finality 均被绑定。
3. 已知 JSON 对象采用 closed-key 检查，重复 key、未知外层字段、明显占位 hash、contract/batch
   self-hash 漂移会被拒绝。
4. 一个 family 中每个 treatment 只有一个 candidate；A1–A5 与 C1–C3 不可混跑；candidate
   bundle 会交叉绑定 executable/model/prompt/console fixture bytes。
5. 当前已列明的 case/oracle marker、launch argv/env/cwd/process/fd/network/endpoint 差异、
   post-grader trigger、额外预算和组件预算攻击会被拒绝。
6. 开发 Authority statement 的 Ed25519 完整性、world/Q/Target/operation 绑定与 U/D/P 形状会被
   检查；P world 中 A1 只能是 `NOT_APPLICABLE`。
7. fixture clone 的 world preimage hash、namespace、keyset、initial-state digest 与所声明的无共享
   路径/通道会被检查。
8. meter ledger 采用封闭 event schema、hash chain 和独立 counter 汇总；不能只改 `observed`
   自报值。
9. run order 必须是全部 run 的精确 committed permutation；fixture 不能提前宣称 CI、可选停止、
   局部修复、runtime-native Effect、Acceptance 或 finality。
10. 最重要的 fail-closed 门已经成立：任何 `ACTUAL_COMPARISON` mode 当前都会被无条件拒绝，
    因而开发 fixture 的自包含 key、文本 artifact 或 controller-shaped receipt 不会被升格为实际证据。

## 仍未关闭的门

这些不是当前开发 smoke 的失败；它们是禁止 actual admission 和更强表述的明确原因：

1. **没有 trusted root/controller seal。** 当前 receipt 是静态、controller-shaped fixture，未锚到
   实际受控进程、OS 观察、append-only 外部域或独立 root receipt。本审计文件本身也不是该 seal。
2. **没有 lawful Authority 证明。** 开发 Ed25519 public key 随 fixture 自带，只证明字节完整性；
   没有可信 Principal key registry，也没有 exact delegation scope、expiry、head、revocation 与
   commit-time currentness 的独立推导。
3. **没有真实 candidate 或 treatment presence。** artifact 仍是 UTF-8 fixture，不是 binary、
   container、模型权重/provider deployment 或可启动 executable；A3 没有真实 provider request，
   A5 没有 `REAL_HUMAN` session，A4/C1–C3 也没有实际运行和 alias/ablation 结果。
4. **没有 runtime-native truth。** Trigger pre/post/native-event 当前只是封存 digest；没有可信事件
   store、Target commit/status/readback、O_Q/O_V Acceptance 或 O_P finality receipt。
5. **没有真实 replicate closure。** fixture 每个 world×treatment 只有一次未运行 admission；没有
   replicate-specific clone/run、seed reveal 与 order 重算、blocked randomization、missingness、
   estimand、CI 或 stop-rule 的实际执行证据。
6. **没有运行时隔离证明。** namespace/keyset/path/channel 当前是 manifest 声明；尚未证明 DB、
   process、provider cache、model context、human carryover、Target/log 与跨 arm 状态真实隔离。
7. **没有完整 treatment 资源与经济比较。** 当前 common interaction meter 不建立 model token/call、
   human minute/compensation、provider charge、ratecard、`C_cold/C_maint/C_exit` 的共同换算或上限。
8. **known-marker scan 不是语义无泄漏证明。** 它关闭了本轮具体 counterexample，但不能排除编码、
   同义改写或真实 executable 内部路由；actual mode 的硬拒绝正是这一边界的必要保护。
9. **S/R twin 尚未运行。** 当前只允许表达 twin shape；Authority-epoch twin、ACK lost、crash、
   duplicate avoidance、revocation 与恢复没有产生结果。
10. **没有 capability、comparison 或完整问题结论。** A3/A5 仍为 `NOT_RUN`；没有任一 CE-001
    case 的新结果、没有 A1–A5 公平比较、没有成本赢家，也不能据此宣称 CE-001、Problem v1 或
    Problem v2 已解决。

## 实际比较所需 root acceptance 最低闭包

下一版本只有同时获得下列实际 preimage/receipt，才可重新审查
`ACTUAL_COMPARISON_SEALED_NOT_RUN`：

- 受信任域中的 controller identity、owner/Principal key registry 与 append-only/root seal；
- 每个 world×treatment×replicate 的 candidate、world、clone、launch 与 isolation receipt；
- 从真实签名 topology 独立推导 U/D/P，并验证 delegation scope/expiry/head/revocation/currentness；
- actual argv/env/cwd/process/fd/network/endpoint 与 candidate executable/container/provider identity；
- trigger native event、reachability、pre/post、causal order 与 Target-prefix 的可重算 preimage；
- controller 原生 budget ledger、A3 provider/model/tool/usage receipt、A5 human/console receipt；
- seed preimage、blocked order、N、missingness、estimand、CI 与固定 stop rule 的闭包；
- Effect/Target readback/Acceptance/finality 的权威原生 receipt；
- 一个绑定全部上述字节、validator、tests、负例结果且带 self-hash 的独立 `ROOT-ACCEPTANCE`。

在这些门关闭前，正确行动不是把开发 fixture 改名为 actual batch，而是继续保持 hard reject。
