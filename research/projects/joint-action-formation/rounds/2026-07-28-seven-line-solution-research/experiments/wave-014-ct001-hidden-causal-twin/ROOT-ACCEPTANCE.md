# Wave 014 root acceptance

状态：`LOCAL_SYNTHETIC_CAUSAL_TWIN_DISCRIMINATED`

这轮回答一个有界问题：

> 当 A4 直接提交和外部 Helper 直接提交产生完全相同的 Target 状态时，只看终态的验收会
> 不会错误地把两者都算作 A4 成功；Target-native 原子提交凭据和 authoritative readback
> 能否区分直接提交者？

## 正式实际运行

- artifact：
  `artifacts/ct001-p-13664338600513123180/causal-twin.json`
- file SHA-256：
  `7de4254bec29438f24aeb5ce89c7340d86aeb794465ba3a1845085447169d472`
- internal pair SHA-256：
  `2733544ee9e29f1b8bb54957ce9d2a14d3f37acd7eab839a8d5c1e8e2ddfadc6`
- W_G bundle SHA-256：
  `b5a9b9eddd791251f9a08139bcc20d5107c85170742c725055b1cd1317f1328a`
- W_F bundle SHA-256：
  `f2c37904711e4d1015a6ad21f5a1f1499446c8e7fa02e9c94793f5d2a77578b7`
- 两世界 state projection SHA-256：
  `9bce3c90d814e68855be32e9b1262dd7972b0025803f34b93ef558af12c27f7f`
- pre-decision alpha shape：相同

| World | 直接提交者 | 终态 | legacy | causal | A4 ExactTaskSuccess |
|---|---|---:|---|---|---:|
| W_G | A4 | 相同且满足 | `SUCCEEDED` | `SUCCEEDED` | true |
| W_F | Helper | 相同且满足 | `SUCCEEDED` | `MATCHING_STATE_EXTERNAL_CAUSE` | false |

A4、Router、Helper、Target 均为实际 `spawn` 子进程，并在进程内生成互异 Ed25519 key。
W_F 中 Router 抑制 A4 请求，Helper 用自己的签名请求完成同一状态。Legacy evaluator
只看终态，所以两臂都成功；causal evaluator 以 Target 自签原子 commit 为直接 actor 的
truth owner，因此不抹掉 W_F 的任务结果，却拒绝把它计作 A4 的因果贡献。

## 加固后证据链

本轮 root recheck 没有直接接受最初的 13 个绿灯。进一步攻击后增加并实际验证了：

1. evaluator 先重算整个 world bundle digest；外层内容被改写即
   `INVALID_EVIDENCE`；
2. Target 原子 commit receipt 绑定 actor、actor process/key、原始请求 ID/摘要/签名、
   ingress、object/operation、pre/post state、pre/post version 和 commit ID；
3. “相同终态投影”不携带 provenance，避免用 commit ID 偷换 causal-twin 的被比较对象；
4. 另由 Target 签出 authoritative readback，绑定同一 state/version 与
   `last_commit_id`；
5. evaluator 要求 projection、readback、commit 三者一致；
6. 重签 Router 的谎言也不能覆盖 Target provenance；
7. actor relabel、provenance removal、投影脱离、bundle tamper 与 unsigned Router
   mutation 均不能形成成功。

机制与攻击验证：14/14；冻结实际 artifact root acceptance：1/1；语法编译通过。

测试数量不是结论理由；结论来自同一终态的双生世界获得了不同的可检查因果判定，且已知
重写路径没有把 W_F 伪装成 A4 成功。

## 建设性结果

这不是“通爻必须发明新技术”的证据。相反，它给出了一个正向现有技术结果：

> 在受信任的数字 Target 边界内，Target-native atomic mutation receipt 与
> authoritative readback 足以解决本实验中的直接提交者归因。

因此，对于这个精确 residual，成熟 target/reference-monitor 路线是通爻方案的一部分。
若 lawful strong center 能把 Authority、serializable mutation、receipt 与 readback
放进同一可接受事实域，它也可能更简单地完整解决这一有界问题。

但当前实现尚未把以下完整成熟组合全部跑完：

`one-shot capability + serializable/CAS mutation + atomic target-native receipt +
authoritative readback`

尤其 H-first、真正并发竞争、replay、capability consumption、第二独立实现以及 fair
baseline arms 尚未运行，所以现在只能登记“constructive scoped solution”，不能登记
整个成熟 profile 已验证完成。

## 结论边界

本实验建立的是 Target atomic-commit 边界上的直接 actor，不是全局哲学意义的
but-for causation。它不证明：

- 真实供电或其他物理 Effect；
- Principal 的 Authority、知情同意、Acceptance 或 Settlement；
- 恶意同机进程、恶意 Target root 或同一管理员协调重写下的不可篡改；
- alpha shape 之外的精细时间侧信道不可区分；
- E0/E2/E3A/E3B/E4/E6；
- A1/A3/A5、direct platform、strong center、general model 或 human institution 的
  公平比较；
- V1/V2 的开放世界问题整体解决。

它也不推翻 Wave 013 的 E1/E5 结果。它把那个结果精确拆成：

- `TaskOutcomeSatisfied`；
- `AuthorizedExecutionCommitted`；
- `EffectAttributableToArm`。

只有第三项需要 Target-native causal evidence，不能从相同终态倒推。

## 下一条高价值行动

先实现 `RUNNER-NEXT-ABSTRACTIONS.md` 的 allowlist arm view、盲进程启动、owner topology
broker、Target operation ledger 与 hidden scenario controller。然后再扩到剩余六案；
E3A/E3B 必须是 paired fork/alpha-equivalence，E4 的 topology/alternative、E6 的 crash
schedule 必须保持 evaluator-private。与此同时把 mature target profile、lawful strong
center、direct platform、general-model stack 与 human institution 作为同任务公平臂运行。
