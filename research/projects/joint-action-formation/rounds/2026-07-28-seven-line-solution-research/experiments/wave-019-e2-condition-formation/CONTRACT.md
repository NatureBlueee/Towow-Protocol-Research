# Wave 019：E2 Condition Formation 可执行合同

日期：2026-07-30  
状态：`LOCAL_SYNTHETIC EXECUTABLE / NO FORMAL MECHANISM PROMOTION`

## 问题

冻结 S0 中数字 Target 能力可模拟存在，但各 owner-native state 明确不存在：

- O_Q 的 exact purpose token；
- O_V 的 C7 短期 delegation；
- O_R 的 resource commitment 与 reservation；
- O_S 的 safety approval。

研究问题是：成熟 workflow/HITL、用途限定 grant、owner state 与 commit-time gate 的组合，
能否首次形成这些条件，随后只产生一个 exact C7 数字 occurrence；以及删除 formation
operator 或 owner 签名拒绝时，能否阻断全部 descendants。

若现有组合完整解决，这就是 E2 的正向解题结果，不要求额外协议增量。

## 独立 owner

每个 case 启动 O_Q/O_V/O_R/O_S/O_P 五个独立 spawn 进程。每个进程：

- 在进程内生成自己的 Ed25519 key，controller 不持有 private key；
- 使用独立 SQLite owner state；
- 使用不同 owner ID、Principal ID 与实际 PID；
- 在 arm 启动前签出 exact S0 absence；
- 在 S0 中签名冻结自己的 decision family、预算、horizon 与 exogenous schedule；
- 后续 response 绑定该 policy head、proposal hash、owner state head、scope、expiry 与 nonce。

broker 只路由 exact bytes、聚合 response，并在 commit-time revalidation 后调用 Target
ledger。broker/controller 不生成或签署 owner token、delegation、commitment、reservation、
safety approval、Acceptance 或 finality。

## 三个实际世界

### baseline

arm 不知道未来 decision。它实际发送 canonical exact proposal bytes。

- O_Q/O_V/O_S 返回独立 `APPROVE`；
- O_R 返回 `COUNTER`，把有效 expiry 调整为 minute 85，并提供 minute 5..50 resource
  window；
- arm 显式接受 counter；
- 四个 owner act 首次从空 S0 形成 exact facts；
- Target execute 前，四个 owner 在各自 current head 上签出 `CURRENT`；
- `TargetOperationLedger` 写入一个 C7 local-synthetic occurrence：duration=45，其他线路为空，
  包含 46 个连续相对样本；每个样本绑定 absolute/relative time、`2.85..3.15kW`
  tolerance、exact `target_id`、自己的 `other_circuits_energized=[]`、
  `safety_ok=true` 与 `noise_ok=true`；
- O_Q/O_V 对 exact receipt/readback 签出 Acceptance；
- O_P 对双 Acceptance 与 receipt 签出 finality。

正确 disposition：`SUCCEEDED_AFTER_FORMATION`。

### REMOVE_FORMATION_OPERATOR

只从 broker capability surface 删除 `FORMATION_PROPOSE` 与 `FORMATION_MATERIALIZE`，其余
startup view、Q 与 S0 scope 不变。

必须为零：

- proposal；
- owner response/sign request；
- owner facts 与 acts；
- Target submit、mutation、receipt、readback；
- Acceptance 与 finality。

正确 disposition：`BOUNDED_UNAVAILABLE_NO_FORMATION_OPERATOR`。

### OWNER_REFUSE

startup view 与 baseline 完全相同；未来 decision 不进入 arm 输入。O_R 在 proposal 后签出
`REFUSE`。arm 必须停止，不 materialize、不 submit Target。

正确 disposition：`BOUNDED_REFUSAL_OWNER_SIGNED`，不能写成 Unknown 或 success。

## Target 边界

`TargetOperationLedger` 是唯一 digital Target mutation path。

- baseline exact target mutation count = 1；
- remove = 0；
- refuse = 0。

Target occurrence 与 46 samples 全部明确标记 `LOCAL_SYNTHETIC`。这只能证明本地数字
状态机闭环，不是物理电路 Effect。

## 独立验收

独立 evaluator 不导入 runtime，也不信任 `suite-result.json`。它直接重算：

- spawn launch surface 与未来 decision absence；
- owner S0、policy、response、act、revalidation、Acceptance、finality 的 Ed25519；
- proposal canonical bytes/hash；
- owner 独立 PID/key/state/principal；
- owner SQLite facts、events 与 state head；
- Target receipt/readback hash、HMAC 与 SQLite identity；
- mutation count，以及 occurrence 的 exact run/world/Q/object/target/operation/proposal、
  duration、deadline、其他线路、46 samples、tolerance、safety 与 noise；
- remove/refuse 的零 descendants；
- 18 个 standalone `DELETE`-journal SQLite 的物理和逻辑 hash。

攻击测试必须拒绝：

- stale/wrong-owner/wrong-scope response；
- formation 前 execute；
- controller forged owner receipt；
- remove 仍形成；
- refusal 被写成 Unknown/success；
- duplicate Target mutation；
- WAL-dependent frozen DB。
- unsafe sample、noisy sample、其他线路送电与 duration gap。
- wrong sample target、逐样本其他线路送电。

## 不宣称

本轮不证明现实法律 Authority、真实 Principal 身份、物理电力 Effect、外部 PKI、恶意
同权限本机防篡改、生产可靠性、跨域泛化、净经济价值或协议整体 relation formation。
