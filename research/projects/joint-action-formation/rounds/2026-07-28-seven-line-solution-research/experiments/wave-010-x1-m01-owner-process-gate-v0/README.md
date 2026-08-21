# Wave 010 X1 M01 owner-signature + process-allowlist gate v0

状态：`STRUCTURAL CANDIDATE / UNSIGNED / IDENTITIES UNRESOLVED / NOT ENFORCED / NOT RUN`

这道门接在 `wave-010-x1-m01-freeze-bundle-v0/AUDIT-002.md` 后面。它没有修改已经接受的
freeze bundle，而是把下一步需要真实满足的 owner 决定和进程隔离写成一个独立候选。

## 已经做成可检验的部分

四个 Authority domain 各有一份独立 request。每份 authorization payload 都逐字绑定：

- freeze bundle 原始字节 hash、content root 和接受审计；
- 本 owner domain 原始字节 hash、owner key ID 和 ledger head；
- relation coordinate、exclusive scope、purpose、current head、not-before 和 expiry；
- `controller 不能代签`、`不授权 runner/commitment/reservation/score writeback` 和
  `不自动激活/晋升`。

Owner 的决定不是在 request 中预填。真实 decision envelope 必须由对应 owner key 对
`AUTHORIZE_EXACT_CANDIDATE` 或 `REFUSE` 签名。缺失、过期、hash 不符、代签或签名无效都按
`NOT_AUTHORIZED` 处理；任一 owner 的有效拒绝产生 `BLOCKED_BY_OWNER_REFUSAL`。即使四方全部
授权，也只到 `READY_FOR_EXPLICIT_USER_DECISION`，不能自动运行。

process allowlist 同时保留四个 owner signer、四个方法 arm、neutral controller 与独立
evaluator 的分离边界。方法只可读 public method-visible 输入，只能写各自输出目录；owner
signer 可读公开的四方 request set，但只能读自己的 private domain、只能写自己的 decision；
controller/evaluator 没有 owner-signature capability。这里没有伪称 OS 能把一个 JSON 文件
按 fragment 隔离。

## 自检真正说明什么

`validate_candidate.py --self-test` 使用只存在于内存的临时 Ed25519 测试密钥，确认：

- 四个 owner 中任意一个都能独立拒绝，其他三个签名不能覆盖它；
- controller 测试密钥不能冒充 owner；
- 改动 bytes/hash/head/purpose/expiry 会 fail closed；
- 四方测试授权仍停在用户决定门；
- 候选 allowlist 没有私有 truth 读取或跨 arm 写入的声明性重叠。

临时测试密钥不是 owner 密钥，自检通过也不是现实 owner commitment 或现实隔离证据。

## 仍未满足

- 没有四个真实 owner 的公钥、私钥提供方、签名、拒绝或组织认领；
- 所有未来进程的 executable path/hash、argv、UID/GID、代码签名、环境与 sandbox profile
  仍为 `UNRESOLVED_EXECUTABLE`；
- 没有 OS 级 deny-by-default enforcement，也没有处理 same-UID 恶意进程、symlink/TOCTOU、
  inherited fd、dynamic import 或网络逃逸；
- 没有 runner、方法、scoreable episode、accepted pair、run 或 coverage；
- 没有任何正式状态变化。

因此下一步不是运行，而是由真实 owner 独立处理 exact requests，同时冻结实际执行文件和
OS 隔离配置；二者经过独立审查后，再把 exact signed/enforced set 交给用户决定是否进入
runner 候选。
