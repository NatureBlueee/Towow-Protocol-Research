# Wave 006 shared task denominator

日期：2026-07-29  
状态：`FROZEN_LOCAL_SYNTHETIC_TASK`

## 任务

Task ID：`W6-STERILE-ROUTE-SIMULATION-001`

两个独立主体需要完成一次有时限的 sterile-route simulation：

- `LAB-SEEK` 只披露最小 route constraints；
- `LAB-OFFER` 只披露最小 simulation window/capacity；
- `SIM-RECIPIENT` 在收到两侧授权内容后运行一次确定性 simulation；
- `BENEFICIARY-REVIEWER` 只验收 frozen output，不自动认领持续合作关系；
- `ANCHOR-W6` 保存 controller decision 与跨域 receipt 的外部锚。

初始 contract：

- world：`W6-STERILE-ROUTE-WORLD`
- evaluation step：`7`
- purpose：`sterile-route-simulation`
- retention：`PT7M`
- one operation：`RUN-STERILE-ROUTE-SIM-v1`
- holder/recipient/controller/anchor 使用独立 synthetic Ed25519 key；
- 所有动作仅限本地合成，不涉及真人、医疗决定或生产资源。

## 统一时序

1. `E0 DECLARED`：主体声明可参与。
2. `E1 PROBED`：当前 operation probe 返回。
3. `E2 DELIVERED`：两侧最小 projection 到达 recipient。
4. `E3 ACKED`：recipient 对精确 bytes 签名 ACK。
5. `E4 DOMAIN_POSTCONDITION`：deterministic simulator 产生 frozen output。
6. `E5 ACCEPTED`：beneficiary reviewer 对精确 output 签 acceptance。
7. `E6 REUSE_REQUEST`：相似但非相同的第二任务到达。
8. `E7 DRIFT`：注入一项 contract/key/authority/environment 变化。
9. `E8 WITHDRAW_OR_RECOVER`：主体撤回，或在重新授权后恢复。

## 各母线不得改变的分母

- G2 只能改变 relation representation/认领层，不能改变 operation、输入、truth 或权限；
- G4 只能改变 reliance strategy，不能让某策略获得更多未来状态；
- G6 只能改变 effect promotion rule，不能删除失败/拒绝；
- G7 只能改变 replay/migrate/re-authorize strategy，不能跳过授权或 acceptance；
- 各实验必须共同保留 `UNKNOWN / REFUSE / ABSENT`，不得统一成失败；
- direct existing/central/human/combined solution 完整解决时算正向成功。

## 统一扰动

至少覆盖：

- probe 后 holder revocation；
- recipient key rotation；
- environment version drift；
- delayed ACK；
- single-side partial materialization；
- beneficiary refusal；
- exact replay；
- same idempotency key / changed command；
- anchor fork；
- schema-compatible alias 与 material semantic change。

## 统一测量

- false positive / false promotion；
- false negative / missed valid action；
- stale reuse；
- recovery time steps；
- disclosure units；
- evidence/coordination operations；
- residual state after withdrawal；
- net task value：

  `accepted task value - disclosure - coordination - recovery - false-action loss`

## 证据边界

本任务只能比较合成机制在冻结条件下的判别力、恢复与成本；不能推断现实频率、医疗安全、
真人接受、商业价值或跨域普遍性。每条线必须说明自己的结果改变什么，不能借共享 task
相互晋升主张。
