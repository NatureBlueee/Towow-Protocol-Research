# Wave 004 status

日期：2026-07-28  
状态：`CONTROLLER_EXECUTION_CLOSED_LOCALLY / NEW_BLIND_WORLD_REQUIRED`

## 本轮改变了什么

G1 HW-B 已经把问题从“匹配找到了但没有执行者”推进到：

> frozen holder authorization 可以经显式 normalization 进入一个受信 controller，
> 形成 direct、derived onward 与 reciprocal counterparty exchange，写入 recipient store，
> 独立磁盘 readback 后签发 execution receipt。

这不是新协议优先的结果。它是把已有的 projection、policy、compatibility、version、
epistemic state 与一个最小 controller 收敛成可复现解决链。

## 三个结果层次

| 结果 | 结论 |
|---|---|
| HW-B V1 `1/8` | 机会发现正确，但 authorization 被错误冒充 execution |
| HW-B V2 `4/8` | controller 真执行；未公开 evaluator 表示约定仍导致四项失败 |
| HW-B V3 `8/8` | post-oracle 表示诊断；只证明剩余差距由三项表示约定解释，不是 blind pass |

所有版本均保持 `3/3 opportunity recall` 与 `0 false wakeup`。

## 已经受攻击验证的能力

- exact replay 不新增 event；
- same key/different payload 零写拒绝；
- changed-contract exact replay 与 pending recovery 零写拒绝；
- tampered audit outcome 与 deleted recipient store 不再返回旧 `EXECUTED`；
- central collection 不再冒充 counterparty exchange；
- counterparty exchange 要求两个独立 recipient store readback。

Wave-004-A 回归 `24/24 PASS`；独立 Agent 重放五个关键攻击全部符合预期。

## 仍未解决

- holder cryptographic signature；
- first recipient 与 final recipient 的独立签名 ACK；
- controller 无权改写的 external append-only anchor；
- derived onward 中 controller 代表 relay 执行的真实授权关系；
- 不同权限域的撤销、并发、恢复和部分故障；
- 一个在修正 method-visible contract 后冻结的新 HW-C blind run。

因此当前正式状态不是“G1 已现实解决”，而是：

`LOCAL_SYNTHETIC_SOLUTION_SUPPORTED / CROSS_AUTHORITY_REALITY_UNKNOWN`

## 下一步

1. 在 HW-C 冻结前公开 depth、reciprocal orientation、status 与 receipt verification 语义；
2. 将 holder/recipient/controller 分到不同权限域；
3. 用签名 authorization、recipient ACK 与外部 anchor 替换 trusted local registry；
4. 重跑新的 blind world，不再使用 HW-B 作为晋升证据。
