# Wave 024 独立验收

## 结论

本轮是 **mixed outcome**，不是全项通过。

在本次冻结的本地合成数字环境、exact Target/操作与合作式进程边界内，现有成熟组合
——签名 delegation/revocation、Target-native durable epoch fence、原子 commit-time gate、
幂等 Effect ledger、签名 status/readback、ACK-loss recovery 以及 owner-native
Acceptance/finality——确实实现了三项有界能力：

- Target 已持久消费 matching revocation fence 后，旧 epoch 请求被原生拒绝且 Effect 为零；
- Target 已提交或已拒绝但 ACK 丢失时，恢复进程能从 exact signed status/readback 收敛，不 replay execute；
- S 的 Acceptance/finality 由 O_Q/O_V/O_P 各自进程、密钥和原生存储产生；R 不产生这些 Effect 后置条件。

但完整的 `CL-024-ISOMORPHIC-BLINDNESS` **失败**。记录中的 payload、argv、env、cwd 和
state path 虽然一致，实验仍固定按 `S → R → U` 运行，candidate 进程与运行根目录处于
同一用户可读取的文件系统中，没有关闭路径、顺序、目录枚举和时间侧面。因此本轮不能被写成
完整的 blind causal twin，也不能由此晋升 Problem V1/V2。

## 逐项状态

| Claim / 更强边界 | 状态 | 独立判断 |
|---|---|---|
| `CL-024-TARGET-CONSUMED-AUTHORITY-FENCE` | `SUPPORT` | 仅限本次 exact Target/mutation boundary 和冻结轨迹；不是 Authority-global currentness。 |
| `CL-024-EXACTLY-ONCE-RECOVERY` | `SUPPORT` | 仅限 proxy 确实丢弃 ACK、source 被 `SIGTERM` 终止、Target 进程仍存活的本地恢复轨迹。 |
| `CL-024-NATIVE-POSTCONDITIONS` | `SUPPORT` | 仅限合作式本地进程边界。实际 S 的 O_Q/O_V/O_P 签名、store 和绑定闭包成立；R 为零。 |
| `CL-024-ISOMORPHIC-BLINDNESS` | `FAIL` | 字节级记录面一致，但固定顺序和同用户共享运行根使 path/order/timing 泄漏门未关闭。 |
| `CL-024-GLOBAL-AUTHORITY-CURRENTNESS` | `NOT_TESTED` | U 中 Authority 已记录 revoke，但 Target 未 ACK matching fence；U raw commit 及后置条件必须保留为 `NOT_SCORED`。 |
| Target process restart persistence | `NOT_TESTED` | 本轮终止的是 candidate source，不是 Target；没有旧 runtime 重启后的 fence/replay probe。 |
| external append-only / pre-run root | `NOT_TESTED` | 顶层已绑定三个 child world semantic hash，但仍是运行目录内的内容寻址，不是 worker/controller 无权改写的外部锚。 |
| A1–A5 比较、现实 Authority/物理 Effect/生产可靠性 | `NOT_TESTED` | 不在 Wave 024 的实际运行范围内。 |

`SUPPORT` 仅指上表的有界本地主张，不将本轮升格为普遍性、生产性或现实世界证明。

## 冻结输入与独立运行

本文只验收以下修复后冻结版；先前 `411978…`、`2a5109…` 与 `twin-618415…` 均已作废，
不被用作证据。

| 对象 | SHA-256 |
|---|---|
| `twin_runtime.py` | `006e2346115143d2e253396a5442814e6064ae17c9e3151713ba9f2e6b4092f9` |
| `run.py` | `b1543a2eb8498dc4ab324494e8a3194e7d0dd1bc3c9ead0d599dcbea2cc66078` |
| `tests/test_runtime.py` | `a2975bfe773e6d8ec04f8b20f1e4857549b5e171b287354321a0e7d71fe172b1` |
| `independent_evaluator.py` | `a2236e616c2e64b8ad3c88e932fe39e02b510bbe18a6c6383dee4b1fdb80fc6e` |
| `QUESTION.md` | `1d4dc5bdf4139396ba7ac76313619aa6c784ab8416639f54853343f730972cb8` |
| `RED-TEAM-PREFLIGHT.md` | `0c3aadf20359eae6604db005aeab422ddc79f8fd51eba31ec36499bb4420b164` |

当前 workspace fresh run：

- run directory：`artifacts/twin-91591fa0c44344839e6c3a23b5dca258`
- TWIN semantic self-hash：`15b806743e79e9c8588b7c7e9db2af1433587fd17485c860ccb3440f311422b9`
- 顶层所绑定的 S/R/U world semantic hash 分别为 `51853700…`、`7873faf3…`、`07b30bdf…`。

独立 fresh reproduction（不读取 workspace artifact）：

- run directory：`/private/tmp/wave024-independent-repro.Ux5477/runs/twin-b9f649935ca04d55aaa81397a9425e68`
- TWIN semantic self-hash：`4d27a4ad446536c9a8def3423e37d42ba3577aadb901bd793fa4d25041e64f67`
- S/R/U semantic hashes：`63d5ba36…`、`31e0f394…`、`c6c3f696…`
- 独立 evaluator 得到同一 claim vector；Authority/Target signatures、四项 predecessor binding
  和 S receipt 在 WORLD/recovery/Target DB 的 exact equality 均被直接重算。

内容语义 self-hash 与 JSON 文件字节 SHA 不是同一对象；本文不将前者误写为外部不可改写根。

## 原生结果重算

独立 evaluator 没有 import `twin_runtime.py`，它以只读方式重开 Authority、registry、Target、
proxy、source 与 owner SQLite store，重算 self-hash/文件哈希、Ed25519 签名、head/event chain、
receipt→readback→Effect→Acceptance→finality 绑定，并核对顶层对 child world hash 的引用。

| World | Target decision | fence / ingress / decision seq | Effect | ACK delivered | source exit | recovery | Acceptance | finality |
|---|---|---:|---:|---|---:|---|---:|---:|
| S | `COMMITTED` | `– / 2 / 3` | 1 | false | -15 | `RECOVERED_COMMITTED_NO_REPLAY` | 2 | 1 |
| R | `REJECTED_STALE_EPOCH` | `2 / 3 / 4` | 0 | false | -15 | `RECOVERED_REVOKED_NO_RETRY` | 0 | 0 |
| U | `COMMITTED`, `NOT_SCORED` | `– / 2 / 3` | 1 | false | -15 | `RECOVERED_COMMITTED_NO_REPLAY` | 2 | 1 |

关键区分是：

1. S 在 Authority 生成 revoke record **之前**已经完成；Authority 进程使用启动时固定的 lab
   root 自行验证完整 S Target certificate、receipt signature、exact scope、epoch/head 与 Effect，
   再在签名 revoke 中绑定 receipt/certificate/request/Effect，而不是信任 controller 裸 hash。
2. R 的 Target-native `FENCE_ADVANCED` 事件序号 2 严格早于 ingress 3，拒绝事件为 4；不是 controller 未发送请求或事后改 reason。
3. U 证明的恰是更强命题未被检验：Authority revoke 记录已存在，但没有 Target-consumed matching fence，所以 raw commit 与原生后置条件可以出现，但不进入 S/R 评分。

## 测试与历史回归

- 最终冻结版 runtime 测试：`24 passed`。
- runtime + independent evaluator 全部测试：`34 passed`。
- 定向 owner/recovery 回归：`6 passed, 11 deselected`。其中 recovery 对有效签名但错配的
  `request_id` / Q / object / Target / operation 全部拒绝；owner 对与 startup 固定 Q 分离的
  Target evidence 拒绝。
- 额外独立回归中，unrelated delegation/Q/actor 和非 revocation status 均被 fence gate 拒绝，
  Target authority head 保持 1、Effect 保持 0。
- 对 owner evidence 的 9 种重签名语义错配（receipt 的 Q/object/Target/operation/actor，
  readback 的 request/receipt/effect/state）全部拒绝。这关闭了早期“签名有效即追加 Acceptance”的缺口。
- wrong-object request、Target/operation alias、expired delegation 以及 lost-ACK 后同 request 幂等性均作为 runtime 回归保留。
- Authority predecessor gate 另覆盖六种保持有效 Target 签名的语义攻击：wrong object、Target、
  operation、decision、epoch 和 durable head，全部在签 revocation 前拒绝。

测试绿灯只支持其覆盖的软件契约，不替代上表中的 claim 边界。

## Blindness 失败的具体原因

本轮保留一个有价值的局部正结果：S/R/U 记录到的 candidate payload、request、process name、
argv、environment、cwd 和 `source_state_path` 相同。

但它不足以支持完整 claim：

- runtime 代码固定先完整运行 S，再运行 R，最后运行 U；
- 三次 candidate 都能从共同 `source_state_path` 回溯到同一 run root；
- run root 与 candidate 处于同一 UID，实际为可读取、可搜索目录；R 启动时 S 的目录/进程历史已经存在；
- 实验没有对目录枚举、进程枚举、时间和调度可见性做隔离或独立测量。

因为冻结 claim 明确要求 case/epoch role 不得经 path/order/timing 泄漏，所以此处必须判 `FAIL`，
不能只因已记录字段相同而降为 `PARTIAL`。

## 当前最高可声称边界

Wave 024 现在可作为一个 **成熟组合的本地功能存在结果**：Target-consumed durable fence、
atomic gate/ledger、signed exact readback、丢 ACK 后无 replay 恢复与 owner-native postconditions 可以组合起来解决
冻结任务中的对应局部问题。这本身就是正向成果，不需要证明通爻独占或额外发明同一能力。

它目前不是完整的 blind causal discriminator，不支持 global instant revocation，不支持 Target restart 后持久性，
没有外部 pre-run/append-only root，也没有测试真实 Authority、物理 Effect、生产可靠性、A1–A5 比较
或 Problem V1/V2 整体解决。

本验收未读取 Pro 返回。后续 red-team 信号发现旧冻结版仅让 Authority 签 controller 提供的
receipt hash，没有 Authority-native receipt verification；该反例已公开重开并产生当前修复版，
旧 artifact 保留但不再支撑结论。
