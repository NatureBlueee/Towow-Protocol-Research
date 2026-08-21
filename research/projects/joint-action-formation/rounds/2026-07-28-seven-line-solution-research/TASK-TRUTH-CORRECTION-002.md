# Task Truth Correction 002 — V0、Q 与 Intent 输入边界

日期：2026-07-29  
状态：`ACTIVE RESEARCH CORRECTION`  
作用域：Wave 010 及后续任务分母；不修改 V1/V2 正典，不覆写 Correction 001 的历史内容

## 为什么必须校正

Pro 独立问题重建暴露了三个会让后续评分失真的冲突。主研究者回读正典后确认，其中
`V0` 冲突是直接文本冲突：

- V1 把 \(V_0\) 定义为“原始价值与不可接受底线”；
- `TASK-TRUTH-CORRECTION-001.md` 第 60 行把 \(V_0\) 写成“公平基线可见和可做的路径”。

后者不能继续被继承。Correction 001 仍作为错误发现与任务降级的历史证据保留；本文件只
修复后续运行语义。

## 立即生效的三个修复

### 1. 保留 V1 的单一 \(V_0\)

后续任务冻结：

```text
V0 = original desired value + unacceptable floor
BE0 = fair baseline observation/action/authority/cost envelope
```

`BE0` 是新增的实验变量，不是 V1 概念，也不能改名回 `V0`。任何方法都不得通过降低
`V0`、扩大自身 `BE0` 或缩小对手 `BE0` 获胜。

### 2. 保留 V1 的唯一 episode-level \(Q\)

七条线可以分别拥有：

```text
A_G1 ... A_G7 = line-local acceptance predicates
T_Gi→Gj = typed transition contracts
Q_episode = V1 qualification predicate Q
```

`A_Gi` PASS 只说明该线的有界输出满足交接条件，不创建新的缩小版问题，也不蕴含
`Q_episode`。不得把 `Q_G1...Q_G7 + Q*` 写成八个互相竞争的正式 Q。

### 3. X1 从 V2 协调接口内的 Intent 开始

V2 明确把 upstream implicit Intent generation 留在当前研究范围之外。Wave 010 X1 的输入
必须冻结为：

```text
INTENT_AT_COORDINATION_INTERFACE
fields may be Unknown
generator / represented Principal / beneficiary / affected party /
decision Authority may be non-coincident
```

X1 可以研究 Intent 的 projection、clarification、qualification、partner discovery 与
relation handoff，但不能把 pre-Intent event→Intent generation 的成功计入 V1/V2。

Wave 009 G1 从 `vague value seed` 开始；在证明该 seed 已经满足 V2 Intent 接口前，它只保留
为 `G1_EXTENDED_BOUNDARY_LOCAL_SYNTHETIC`。若未来单独研究 upstream generation，必须明确
标成辅助扩展问题，不得静默进入 V1/V2 coverage。

## 伴随校正

1. “没有等价路径”只能相对于冻结的 transition model、action grammar、Authority
   envelope 与 search bound 判断；开放世界外保持 Unknown。
2. zero-disclosure paired worlds 的在线正确输出是 calibrated `Unknown / Reject / Defer`。
   只有独立 oracle 证明全部合法 observation/probe 路径被 policy 阻断时，才能在该冻结范围
   写 `POLICY_UNDISCOVERABLE`；不得把它误写成现实机会不存在。
3. 必要 rights holders、affected Principals、Authority Loci 与 target witness 仍由 truth
   冻结；待发现且可替代的 role-filler identity 可以对方法隐藏。冻结不等于 method-visible。
4. semantic equivalence、material change 与 \(V_0/Q\) 变化需要独立 evaluator 和相应
   Principal/adjudicator 来源；一个 synthetic mega-oracle 不能代签全部规范事实。
5. T5 比较 `DIRECT_PLATFORM / LIGHTWEIGHT_ADAPTER / FULL_RELATION_FORMATION`，但作为
   collapse gate 单独报告，不进入正任务平均分。

## 数量不是真值分母

Pro 提出的 X1 `66 worlds` 与 X2 `72 worlds` 只保留为待审查的运行预算草案：

- motif 尚未全部以 `S0/V0/BE0/Q/input/oracle` 实例化；
- identifier/order permutations 是 metamorphic replay，不是新增 truth worlds；
- T5 是单独 negative control/collapse gate；
- X2 的 scoreable population 必须由 finalized X1 实际输出决定，不能预先用手写成功
  relation 填满。

所以这两个数字都不是理论最小、coverage 分母或 release requirement。

## X1 与 X2 的强制交接门

X1 只产生 `AUTHORITY_VALID_FRONT_HALF_CANDIDATE` 或 typed non-success。它们的唯一
当前合同是
[`WAVE-010-X1-OUTCOME-CONTRACT-v0.json`](./WAVE-010-X1-OUTCOME-CONTRACT-v0.json)。
每个 `X1Outcome` 必须绑定合同版本、schema hash、reason-registry 版本/hash、原始 method
return bytes，以及 G1/G2/G3/G5 四条线和四个 transition contract 的 raw receipt refs。

顶层 category 至少完整保留：

```text
AUTHORITY_VALID_FRONT_HALF_CANDIDATE
REJECT
DEFER
UNKNOWN
INVALID
REVOKED
EXPIRED
BOUNDED_UNREACHABLE
SAFE_EXIT
UNRESOLVED_SCHEMA
```

`reason_code` 必须是当前 registry 中该 category 下的精确已登记值。不得用宽泛的
`DENY/BLOCKED/UNKNOWN/INVALID` 丢失 G5 的
`REQUIRE_APPROVAL / STALE_VERSION / RESERVATION_REQUIRED /
RESERVATION_CONFLICT / REVOKED / EXPIRED`，也不得丢失其他线的精确 non-success。
四条 line receipt 与四条 transition receipt 即使未到达，也必须提供 owner 签名的 typed
`NOT_REACHED` receipt，不能用 `null` 或省略表示。

遇到未知 schema/version、未登记 category、未登记 `reason_code`、category/reason
不匹配、缺失 receipt 或 schema/registry hash 不一致时，必须 fail closed 为
`UNRESOLVED_SCHEMA`，保留原始 bytes hash 和失败原因；不得把它归一化为
`UNKNOWN`、`INVALID` 或任一已知业务结果。

X2 主评分必须：

1. 读取 finalized X1 的原始 bytes，并绑定 `run/world/arm/output` hash；
2. 绑定 X1 的 `S0/V0/BE0/Q_episode`、input、model、oracle、evaluator 与 owner receipts；
3. 每个 arm 只继承自己的输出，不能共享 canonical successful relation；
4. 无损传递上述全部 category、已登记 `reason_code`、四线 raw receipts 和 transition
   receipts；不得删除、合并、改名或提升任何分支；
5. 机械复核 receipts/current heads，不能读取 X1 PASS 后据此制造对象；
6. 在读取方法输出前独立冻结 X2 的 holdout、Effect、Acceptance 与 dependency truth；
7. 拒绝手写等价对象、跨 world/arm transplant、旧 head、缺 owner 与重复 reservation；
8. 只把 canonical fixture 用于 runner 单测，并标记 `FIXTURE_ONLY / NOT_SCOREABLE`。

本校正不使 X1 或 X2 变成已运行，也不改变 Problem、MechanismProfile、NAC 或任何稳定主张。

## G5 四域权威闭包补充

G5 不得继续把 program coordinator、delta calibration、independent validation 与
site-data steward 压成一个可由中心维护的 truth package。四个 authority domain 必须分别
持有 private truth、owner key、ledger/root candidate、S0 和 transition receipt rules；
聚合片段只绑定四份原始文件的 SHA-256，并验证组合闭包，不得内嵌、生成、改写或代签域真值。

S0 继续冻结为：relation
`relation-estuary-sensor-calibration-joint-bid@v1` 尚为 `PROPOSAL_NOT_FORMED`，四域
Commitment 均未创建，delta 所有的 field-service slot 为 `AVAILABLE_UNHELD` 且 Reservation
未创建。强中心可以调用和编排全部合法接口，但不因此成为任何域的 truth owner。

G5 成功必须逐项读回并验证：

1. 四域各自当前 Mandate、stance、Commitment 与 head 的本域 owner receipt；
2. delta calibration resource owner 单独签发的原子 Reservation receipt；
3. 所有 receipt 的 relation coordinate、版本、scope、freshness、revocation 与 signer domain；
4. 不存在用单一 Commitment、聚合签名或跨域 controller substitution 代替上述闭包。

任一阻断必须输出
[`WAVE-010-X1-OUTCOME-CONTRACT-v0.json`](./WAVE-010-X1-OUTCOME-CONTRACT-v0.json)
当前 reason registry 中一个精确的 `category/reason_code` 对；不得使用包含多个可能原因的
复合桶。缺失已登记 reason 时先扩展 registry；无法判定 schema 或 pair 时保持
`UNRESOLVED_SCHEMA`，不得猜成业务结果。
