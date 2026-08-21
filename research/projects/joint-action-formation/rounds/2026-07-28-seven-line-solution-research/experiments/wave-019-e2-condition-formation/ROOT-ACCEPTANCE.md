# Wave 019 ROOT 独立验收

日期：2026-07-30  
状态：`ACCEPTED_LOCAL_SYNTHETIC_E2_MATURE_WORKFLOW_HITL_SCOPED`

## 冻结对象

正式 suite：

`artifacts/suite-5909e01158ad4e6f9f765f2aa45909fc`

冻结哈希：

`49154f083738a2c244424e8bcacb74a0fb46b23a9f310358407e4c49e3823684`

正式文件：

- `ROOT-FREEZE.json`；
- `ROOT-INDEPENDENT-ACCEPTANCE.json`；
- `ROOT-FROZEN-SQLITE/` 中 18 个 standalone `DELETE`-journal DB；
- `evaluator.py`。

每个 frozen DB 同时绑定物理文件 SHA-256 与逻辑表快照 SHA-256。正式 evaluator 只读取这些
standalone DB；原 runtime DB/WAL/SHM 只作 provenance。

## 独立验收结果

- 三个 case 共实际启动 15 个 owner process、3 个 broker 与 3 个 blind arm；
- 每个 case 中五个 owner 的 PID、key、SQLite state 与 Principal ID 全部不同；
- O_Q/O_V/O_R/O_S 的 exact S0 必要条件均由各 owner 签名为 `ABSENT`；
- owner 自己在 S0 签名冻结 decision family、预算、horizon 与 exogenous schedule；
- baseline 与 refuse 的 arm startup view 完全相同；
- remove 除删除 formation capability 外，与 baseline startup view 相同；
- baseline arm 实际发送 proposal canonical bytes；
- 四份 response 分别绑定 proposal hash、owner head、policy head、scope、expiry、nonce；
- O_R `COUNTER` 被 arm 显式接受，随后 owner act 首次形成五类必要 operative facts；
- 四份 commit-time revalidation 均来自对应 owner key/current head；
- Target ledger 只产生一个 C7 local-synthetic occurrence/readback；
- occurrence exact 绑定 run/world/Q/object/target/operation/proposal，显式
  `duration_minutes=45`、`other_circuits_energized=[]`；
- occurrence 有 46 个 offset `0..45` 的连续 synthetic samples，absolute time 为
  `start+offset`；每点自身均绑定 exact `target_id`、
  `other_circuits_energized=[]`、`2.85..3.15kW`、`safety_ok=true`、
  `noise_ok=true`，且 `start+45<=deadline`；
- O_Q/O_V 双 Acceptance 与 O_P finality 均绑定 exact Target evidence；
- remove 的 proposal/owner facts/Target descendants 全部为零；
- refuse 的 O_R `REFUSE` 有效且被正确判为 bounded refusal；
- broker/controller owner-fact 签名数为零；
- 18 个 accepted SQLite 均 `journal_mode=delete`、`quick_check=ok`，无 WAL/SHM/tmp
  companion。

## 攻击结果

独立 evaluator/attack tests：`17 passed`，其中 16 个攻击实例覆盖：

1. stale response head；
2. wrong owner；
3. wrong scope；
4. formation 前 Target execute；
5. controller key forged owner act；
6. remove run 仍写入 purpose token；
7. signed refusal 被误写 Unknown；
8. signed refusal 被误写 success；
9. duplicate Target commit event；
10. frozen DB 回到 WAL dependency。
11. sample `safety_ok=false`；
12. sample `noise_ok=false`；
13. `other_circuits_energized` 非空；
14. occurrence duration gap；
15. sample 指向错误 Target；
16. 单个 sample 的其他线路非空。

Wave 015 visibility/Target ledger 回归：`21 passed`。

## 接受结论

> 在冻结的 local-synthetic E2 世界中，成熟 workflow + 独立 HITL owner act + purpose-scoped
> grant + reservation + commit-time policy gate 能从 owner-native S0 空状态首次形成所需
> 条件，并只产生一个 exact C7 digital occurrence。移除 formation operator 或收到 owner
> 签名拒绝会阻断全部 formation/Target descendants。

这是现有成熟技术组合对 E2 有界问题的正向解决方案。

## 未证明

- 法律 Authority 或现实 Principal 身份；
- 物理电路 Effect、物理 telemetry 或现实安全；
- 外部 PKI/身份锚；
- 同权限恶意本机进程下的不可篡改；
- 生产可靠性、长期漂移、跨域泛化或净经济价值；
- 协议整体 relation formation 或正式机制晋升。

这些未证明项限制结论作用域，但不否定本轮 local-digital E2 解题结果。
