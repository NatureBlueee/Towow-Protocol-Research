# Wave 006-C effect ladder and safe reopen

状态：`LOCAL_SYNTHETIC_COMPOSED_SOLUTION_SUPPORTED`

共享任务：`W6-STERILE-ROUTE-SIMULATION-001`  
共享任务 SHA-256：
`0cde980b1cd9754d61e1cc2f9478a85c9f587ec5fb5b4e7c07ccb068fbc100a3`

本实验只改变 G6 的 effect promotion rule 与 G7 的 reopen strategy。operation、冻结 truth、
purpose、初始 retention、holder/recipient/beneficiary 权限和拒绝权均来自共享任务；不读取
HW-C private、oracle、tests 或 local packet。

## 当前结果

在这个冻结合成任务内，不需要新的通爻协议机制。以下成熟组合已经完整解决受检验问题：

- Ed25519 signed receipts 区分 authority；
- 强中心 workflow 负责 idempotency、阶段编排和恢复；
- event-sourced external anchor 绑定 delivery decision；
- schema migration adapter 只处理白名单同义别名；
- material drift 进入明确的 re-authorization workflow。

这是正向通爻成果：现有技术的有界组合可以复现，并且明确知道何时不能复用。

## 五级 effect ladder

| 级别 | 状态 | 独立晋升条件 |
|---|---|---|
| L0 | `ATTEMPT` | controller 对冻结 action 签 attempt |
| L1 | `DELIVERY` | controller delivery receipt + controller 无权签发的 external anchor |
| L2 | `RECIPIENT_ACK` | recipient 对两侧精确 delivery bytes 和 anchor 签 readback ACK |
| L3 | `DOMAIN_POSTCONDITION` | deterministic simulator 对冻结 output/state root 签 postcondition |
| L4 | `BENEFICIARY_ACCEPTANCE` | beneficiary 对精确 output 签 acceptance |

L2 以前的“漂亮 delivery”不能证明 operation 成功；L3 也不能替 beneficiary 接受。四个
predecessor-self-promotion mutation 分别让上一级 signer 伪造下一层，结果均停在原层：
`false promotion = 0/4`。

## 三种 reopen 策略

三策略看到完全相同的 case、历史 package、current contract 和冻结 truth：

1. `IMMUTABLE_REPLAY`：只在 exact bytes/contract 未变时重放或从已验证阶段恢复；
2. `MIGRATION_ADAPTER`：只转换 allowlisted、无语义变化的 schema alias；
3. `REAUTHORIZE`：material contract、key、recipient 或 environment drift 后生成全新的授权、
   ACK、postcondition 和 acceptance 链；旧 effect 只作为历史证据。

最优结果：

| drift case | 最优策略 | 合成净值 | 恢复步 |
|---|---:|---:|---:|
| exact replay | immutable replay | 100 | 0 |
| ACK 后 partial recovery | immutable replay | 92 | 2 |
| delayed ACK | immutable replay | 88 | 3 |
| schema-compatible alias | migration adapter | 96 | 1 |
| contract semantic change | re-authorization | 76 | 5 |
| key rotation | re-authorization | 76 | 5 |
| recipient withdrawal | re-authorization | 76 | 5 |
| environment material change | re-authorization | 76 | 5 |
| anchor fork | re-authorization on a healthy current chain | 76 | 5 |
| single-side partial materialization | re-authorization | 76 | 5 |
| holder revocation | safe rejection | — | — |
| beneficiary refusal | safe rejection | — | — |

这里的净值是固定合成权重
`accepted value - disclosure - coordination - recovery - false/stale loss`，只用于同分母比较，
不是商业价值或现实频率。

## 关键区分

- exact replay 与 material semantic change 不能共用一个“兼容”判断；
- key rotation 不使旧 receipt 的历史事实消失，但旧 key 不能签当前 effect；
- recipient withdrawal 后，旧 effect 被归档，新 recipient 的 effect 使用新 contract；
- schema alias 不能遮蔽 anchor fork 或 beneficiary refusal；
- same idempotency key + changed action digest 被拒绝；
- single-side materialization 不到 L1，不能借 `partial` 名义晋升；
- `UNKNOWN / REFUSE / ABSENT` 保持三种 terminal observation，不压成失败。

## 证据边界

结果仅支持：

> 在共享合成任务、固定签名 authority、确定性 simulator、单一 pinned external anchor 和受信
> workflow controller 下，五级 verifier 与三策略组合能够阻止受检验的 false promotion、
> stale reuse，并以较低成本恢复仍有效的 partial action。

不支持现实主体接受、医疗安全、生产可靠性、跨数据库 Byzantine atomicity、多观察者 anchor
equivocation 检测或跨域普遍性。`16/16` 测试与 `0/4` false promotion 只证明当前 fixtures 和
实现。

## 运行

```bash
PYTHONPYCACHEPREFIX=/tmp/wave006-effect-pycache \
  python3 -m unittest discover -s tests -v

python3 evaluator.py --output results.json
```

