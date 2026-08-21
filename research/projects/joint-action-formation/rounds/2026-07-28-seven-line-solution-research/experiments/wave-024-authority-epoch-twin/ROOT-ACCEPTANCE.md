# Wave 024 Root Acceptance

日期：2026-08-01  
状态：`ACCEPTED MIXED SCOPED LOCAL SYNTHETIC RESULT / POST-ACCEPTANCE REPAIRED`

## 结论

本轮得到一个正向但有界的现有技术组合解，而不是一个新协议必要性结果：

```text
signed versioned delegation/revocation
+ Target-consumed durable monotonic fence
+ Target-local atomic gate / Effect-or-refusal ledger
+ stable request digest and idempotent terminal receipt
+ independent ACK-drop boundary
+ exact signed status/readback recovery
+ owner-process pinned trust and native Acceptance/finality
```

在最终冻结的本地数字 Target、合成 Authority 与合作式进程隔离下，这个组合支持三个 claim，
反驳一个 claim，并把一个更强 claim 留在未检验状态：

| Claim | Root 决定 |
|---|---|
| `CL-024-TARGET-CONSUMED-AUTHORITY-FENCE` | `SUPPORT_SCOPED` |
| `CL-024-EXACTLY-ONCE-RECOVERY` | `SUPPORT_SCOPED` |
| `CL-024-NATIVE-POSTCONDITIONS` | `SUPPORT_SCOPED` |
| `CL-024-ISOMORPHIC-BLINDNESS` | `FAIL` |
| `CL-024-GLOBAL-AUTHORITY-CURRENTNESS` | `NOT_TESTED` |

前三项成功不是因 Towow 独占，而是因为成熟 primitive 被放到正确的 truth-owner 和原子边界中。
这正是通爻方案的正向成果：该 residual 不需要重复发明；以后比较的是适用域、依赖、成本、迁移
和失败恢复。

## 最终冻结对象

- runtime SHA-256：`006e2346115143d2e253396a5442814e6064ae17c9e3151713ba9f2e6b4092f9`
- workspace fresh run：`artifacts/twin-91591fa0c44344839e6c3a23b5dca258`
- TWIN canonical semantic self-hash：
  `15b806743e79e9c8588b7c7e9db2af1433587fd17485c860ccb3440f311422b9`
- independent evaluator SHA-256：
  `a2236e616c2e64b8ad3c88e932fe39e02b510bbe18a6c6383dee4b1fdb80fc6e`
- independent evaluation：
  `artifacts/twin-91591fa0c44344839e6c3a23b5dca258/INDEPENDENT-EVALUATION.json`
- independent fresh run：
  `/private/tmp/wave024-independent-repro.Ux5477/runs/twin-b9f649935ca04d55aaa81397a9425e68`
- independent-run TWIN semantic self-hash：
  `4d27a4ad446536c9a8def3423e37d42ba3577aadb901bd793fa4d25041e64f67`

`twin_artifact_sha256` 明确是删除 self-hash 字段后的 canonical JSON semantic hash，不是
`TWIN-ARTIFACT.json` 文件字节 hash，也不是外部不可改写锚。顶层现在绑定 S/R/U 三个 child
world semantic hash；运行目录外的 append-only root 仍未建立。

先前 runtime `411978…`、`2a5109…` 以及运行 `twin-618415…` 只作为失败和修复历史保留，
不进入本决定证据。`twin-618415…` 的具体失败是：Authority 签了 controller 送入的 predecessor
hash，却没有自己验证 Target certificate、receipt signature 和 exact scope；因此不能作为
Authority-native 因果前驱证据。

## 原生结果

| World | Authority / Target 顺序 | Target | Effect | ACK | recovery | Acceptance / finality | 评分 |
|---|---|---|---:|---|---|---:|---|
| S | S commit 后 Authority 才签 revoke | `COMMITTED` | 1 | proxy 丢弃 | no replay | `2 / 1` | S/R discriminator |
| R | Authority revoke → Target durable ACK → ingress | `REJECTED_STALE_EPOCH` | 0 | proxy 丢弃 | no retry | `0 / 0` | S/R discriminator |
| U | Authority revoke 已存在；Target 未安装/ACK fence | raw `COMMITTED` | 1 | proxy 丢弃 | no replay | `2 / 1` | `NOT_SCORED` |

U 不是失败噪声。它直接说明：Authority 的远端撤销记录、签名、workflow 或最终 owner receipt
不能自动建立 Target commit 之前的跨域顺序。若真实任务要求 global instantaneous revocation，
必须另外采用共享 transaction/sequencer、可消费 one-shot permit，或明确有界 lease/失效窗口；
继续增加 RAG、目录、manifest 或 controller 日志不解决这个结构问题。

## Root 与独立复核

- runtime tests：`24 passed`；
- runtime + independent evaluator：`34 passed`；
- 独立操作者未使用 workspace artifact，在新 `/private/tmp` root 重跑同一冻结源码得到相同
  claim vector；S/R/U semantic hashes 分别为 `63d5ba36…`、`31e0f394…`、`c6c3f696…`；
- evaluator 不 import runtime，直接读取 Authority、registry、Target、proxy、source 和 owner
  SQLite，重算文件/self hash、Ed25519、head/event chain 与
  receipt→readback→Effect→Acceptance→finality；
- owner/recovery 定向回归重新签出内容有效但 Q/request/object/Target/operation/readback 关系错误的
  输入，最终实现全部 fail closed；
- unrelated delegation/Q/actor、非 revocation successor、wrong object/Target/operation、expired
  delegation 和 request-ID rebound 均作为回归保留；
- 新增六类“签名仍有效但 predecessor 语义错误”攻击：wrong object/Target/operation/decision/
  epoch/head 均由 Authority 进程在签 revoke 前 fail closed；
- `INDEPENDENT-AUDIT.md` 的复核没有读取 Pro 返回。

测试通过只支持这些明确覆盖的本地软件契约。它不把合成签名变成法律 Authority，也不把数字
Target state 变成现实物理供电。

## 失败与未覆盖边界

完整 `ISOMORPHIC-BLINDNESS` 必须保留为 `FAIL`。虽然记录到的 payload、request、argv、env、
cwd 和 state path 相同，runner 固定按 S→R→U 执行，candidate 与其他域处于同一 UID 和可枚举
文件系统中，路径、历史、调度和 timing side channels 未关闭。因此 Wave 024 不能作为 A1–A5
公平比较的 blind run，也不能因为另外三项支持而改写此失败。

以下保持 `NOT_TESTED / NOT_ESTABLISHED`：

- Authority-global instantaneous revocation；
- Target 自身 crash/restart 后 fence 单调性；
- semantic alias、旁路 endpoint 和 transient Effect 的一般闭包；
- hostile same-UID filesystem/process/write resistance；
- 外部 pre-run/append-only root；
- 法律 Authority、物理 Effect、生产可靠性、现实 owner 认领；
- A1–A5 或 C1–C3 比较、成本 Pareto、总体赢家；
- Problem V1/V2 完整解决。

## 对下一步的改变

Wave 024 已关闭“是否必须为 Target-consumed fence + ACK-lost recovery 发明新 primitive”这一
问题：当前没有必要。下一项高价值工作不是美化本 twin，而是分开推进两个仍承重的证据缺口：

1. 用随机化 clone 顺序、candidate 无法读取的独立运行根/权限域和可测 timing envelope 重建
   公平 blind runner；否则 A1–A5 的任何胜负仍可能来自 world 泄漏。
2. 对同一 Target state machine 做 `execute LP < fence LP`、`fence LP < execute LP`、
   post-check/pre-commit 插入、Target crash/reopen 和 semantic alias/duplicate 调度枚举；这决定
   本轮的指定轨迹结果能否加强为并发/恢复性质。

只有上述共同分母关闭后，才运行 A1–A5/C1–C3 actual comparison。Wave 024 自身比较次数仍为
`0`，winner 为 `NONE`。
