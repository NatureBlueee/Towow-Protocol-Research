# Wave 005 status

日期：2026-07-28  
状态：`TRUTH_AND_CROSS_AUTHORITY_KERNEL_READY / BLIND_SOLVER_EXTERNAL_PAYLOAD_BLOCKED`

## 已完成

### HW-C truth/evaluator

- 全新世界，不是 HW-B 实体改名；
- 11 个物理隔离 local packet；
- method-visible 明确公开：
  - depth 单位、起点和累计规则；
  - reciprocal 对称与 orientation；
  - terminal status 枚举；
  - controller receipt、全部 recipient ACK、external anchor 的验证语义；
- `19/19` truth/evaluator self-tests PASS；
- 15 个冻结 falsifier；
- 未生成 candidate。

在 candidate 提交前，root/solver 未读取：

- `controller_input.json`；
- `delivery-packets/controller-index.json`；
- `private/**`；
- `tests/**`。

### Cross-authority receipt kernel

- holder、controller、recipient、external anchor 四个独立 Ed25519 权限域；
- direct 需要 recipient ACK + external anchor；
- derived 需要 first recipient 签名 onward authorization；
- reciprocal 在双方 commit ACK 前不返回 `EXECUTED`；
- revocation、idempotency、key rotation/expiry 与 crash recovery；
- `13/13` 攻击测试 PASS；
- 9 项 manifest artifact hash PASS。

已明确的未覆盖边界：

- reciprocal 保证 decision/success-claim atomicity，不保证崩溃期间绝无短暂单边
  materialization；
- single pinned anchor 不能解决多 client equivocation；
- 仍是本地合成模拟。

## 当前阻塞

HW-C 要求每个 local packet 由 fresh isolated solver 处理，不能由同一上下文连续读取 11 个
packet。collaboration thread slots 已被 completed agents 占满，因此建立了严格白名单的本地
`codex exec` runner：

- 每次只发送 method-visible README；
- submission schema；
- 一个 HW-C synthetic local packet；
- 不发送 coordinator、其他 packet、private、tests 或 controller-index；
- 保存 packet hash、prompt、model、stdout/stderr 与 exit。

首次 FALLOW-26 尝试在 sandbox 内无法初始化 Codex app-server；固定 runner 的 escalation 又被
安全审查拒绝，理由是缺少用户对“精确 payload + 精确 provider”的明确授权，并明确禁止绕行。
当前完成 `0/11`，solver 没有读取任何 local packet 内容。

失败审计：
`runs/wave-005-a-held-out-world/g1/t1-hw-c/candidate-isolated-runs/FALLOW-26/exit.json`

## 需要的精确授权

> 允许把 HW-C 的 `method-visible/README.md`、`method-visible/submission_schema.json`，以及
> 每次一份 synthetic local packet，发送到本机 Codex 当前 OpenAI provider
> `gpt-5.6-sol`，共 11 次 blind extraction；不得发送 coordinator、其他 packet、
> `controller_input.json`、`controller-index.json`、`private/**` 或 `tests/**`。

在获得该授权前不启动 candidate，不以同一上下文读取所有 packet，也不绕过安全审查。
