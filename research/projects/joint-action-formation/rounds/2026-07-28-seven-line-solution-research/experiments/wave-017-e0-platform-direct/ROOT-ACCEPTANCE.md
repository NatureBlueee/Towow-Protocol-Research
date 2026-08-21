# Wave 017 ROOT 独立验收

日期：2026-07-30  
状态：`ACCEPTED_SCOPED_LOCAL_SYNTHETIC_U_PLATFORM_DIRECT`

## 冻结对象

- 正式 batch：`batch-8672988589969883`
- pair summary SHA-256：
  `dc446758e3751b30f64f8ce794a620091117c1c60e9ce885c64bf4440bfde415`
- ROOT acceptance SHA-256：
  `eec9d5944812b374714b0c7962cdf91f2687f4b1a84cfbb75323484461cc6001`
- 机器验收：`artifacts/ROOT-ACCEPTANCE.json`

独立 evaluator 不导入运行实现或 Wave 015。它从冻结 Authority 公钥与签名 grant、原始
artifact、SQLite event ledger、Target HMAC receipt/readback、资源锁、双角色 Acceptance
与 finality 重新判断。

## 接受结论

在冻结的 `U / LAWFULLY_UNIFIED` 本地合成世界中：

- 平台原生 policy/IAM、内部资源锁和成熟 Target ledger 只用一次 native call 完成 exact
  数字任务；
- Target 只出现一次提交，actor 为平台，readback 与提交绑定；
- requester/venue 两个角色的 Acceptance 与 `NO_EXTERNAL_TRANSFER_DUE` finality 均可验签；
- discovery、relation、delegation、external transfer 的零计数来自平台 SQLite event rows
  独立重算；
- removal world 与正控共享同一 frozen input、opaque run 和 grant subject，只把 signed
  direct Authority 从 `PRESENT` 改为 `REMOVED`，随后 policy 拒绝且零锁、零 Target
  mutation、零外部 formation。

因此：

```text
LAWFULLY_UNIFIED_PLATFORM_NATIVE_EXISTING_COMPOSITION
= POSITIVE_SCOPED_SOLUTION
```

这是通爻的正向解题结果；不因组件均为现有技术而降级。

## 防泄漏与攻击

arm 是真实 `spawn` child，使用 opaque argv/process name、空白中性 cwd、固定最小环境和
generic interface。启动面和 transcript 不含 E0、Wave 017、platform-direct、applicability、
removal-counterexample、expected/result oracle。测试覆盖 Authority key 伪造、外部事件
注入、Acceptance 篡改、数据库调换、假 spawn、visibility 泄漏和第二次 native call。

当前验证：`16/16 passed`，语法编译通过；正式四个 SQLite 为 standalone `DELETE` journal，
无 WAL/SHM/tmp companion。

## 未证明

- 真实物理送电或物理 telemetry；
- OS 级网络无旁路；
- `P / PLURAL_INDEPENDENT` 多主体协调；
- CE-001 全 family；
- 长期维护、停更、迁移和净经济成本；
- 对恶意同目录 writer 的不可篡改。

`EffectAttributableToPlatform` 只表示本地数字 Target 的直接提交归因，不是全局或物理因果。
