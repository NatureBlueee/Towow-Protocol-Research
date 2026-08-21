# Wave 025 pre-formal real-smoke ledger

日期：2026-08-01  
状态：`FIVE PRESERVED ABORTS + ONE CLOSED STRUCTURAL SMOKE / NO QUALIFICATION VERDICT`

本文件只保存改变实现或研究判断的最小失败谱系。A–E 都是不同 `batch_id` 的本地 smoke；没有一批
被补跑、拼接、reveal 或改写为资格证据。原始批次保存在 `/private/tmp`，不属于长期正典包。

| batch | precommit SHA-256 | external Git blob | closed SHA-256 | 观察结果 |
|---|---|---|---|---|
| A | `621478778c734944e28412d7956894ea94ca4f6d548902678a65cea358bc2528` | `321cfa5d9990df4e6b21a98383fbe5296ccab6b0` | `c67fb0db4a5b2707b8e4de21c39409875360da278513733c239b817f98236e2d` | Docker Desktop 拒绝显式 `--pid private`；首 slot 启动前失败，batch `ABORTED`。 |
| B | `e0d8f1e4d9d2edd037c18a50f348142dda04ee378f51070c603dec84a168146b` | `b321b41357a0fe6687b4f73624a9d545dd4ff3a1` | `d049b33622a6b14d116c8bb89d3768219945f44d3a05151ebdd43f62ddc54361` | Docker Desktop 拒绝显式 `--uts private`；首 slot 启动前失败，batch `ABORTED`。 |
| C | `7f5dfe49f6e8513df8f6b3b48dcc5b55a50c8ea0d9d6f6af7cc73ea8853fdd90` | none | none | prepare 绑定了错误的 feature-spec hash；在锚定与运行前发现，保留为 `PREPARED_INVALID_UNANCHORED`。 |
| D | `d2b0d2ddd58ebc36159d76a2fc12eeefbc26c04c01dddb507a32555b569d10ae` | `9071a5b11b1050b996b510c3172eb7b821bc45d8` | `037656262ff12beecb88be3f9564c9eb9d9b6580eca58d9b202bb9ae2e1dca27` | 12/12 collector exit 0，stdout 非空；stopped container 的 `/out` tmpfs 不可由 `docker cp` 读取，12 个 slot 均缺 out，batch `ABORTED`。 |
| E | `9265a7056fb54ea966341ae1507d490207bf759a33ce81ba62b6e8546ac09ff2` | `17485c8d2ae387aba5f30d00d06b262514e7cc5c` | `136e6a7d9aaeba8ad9d7eeb8483b3fcff16e39f6eefbdbc24188a5bfc429825d` | PID 1 supervisor 证实 collector 已退出、ready 存在且 container 仍 running，但 Docker archive API 仍看不到 tmpfs；12 个 slot 均为 `SUPERVISOR_PROTOCOL_MISMATCH`/缺 feature，batch `ABORTED`。 |
| F | `d9a44ab9a5a781a90b70e25ff2a448a329c151ca19998255a2d4d6b45904a77e` | `d78f436b9959a31c29f1c303f8a5a85db3b473af` | `26471d579c13a3f26261512c1d9ac1c67516cb3f610840afa7c8c1f16c42cb5e` | V1.3 post-cut protocol：12/12 `COMPLETE`，D0/D1/T 各 4/4；每槽 19 daemon events、5 个登记 exec group、无额外 exec；reveal `7f698271d211441ad46b6851d8b219238f6e81b87f72afbdcf6de579adb70287` 全重建。旧 evaluator 按未知 precommit 字段与共享歧义正确输出 `NOT_QUALIFIED`，evaluation SHA `7edd1c573ffa042a6b7a30d2d2ab8e7877ffdd8b75643dbd18cc9f7a7c943bc0`。 |

## 这些失败改变了什么

1. `--pid private`、`--uts private` 不能只因文档或其他 runtime 支持就写进本机实际命令；本机默认
   namespace 必须由 actual inspect 证明，unsupported spelling 不等于 isolation failure。
2. `/out` tmpfs 与“不挂载可写 host evidence”仍然是正确边界，但 Docker Desktop 的 archive API
   不提供该挂载的证据读取能力；`docker cp` 在 stopped/running 两种状态都已被真实反例否定。
3. V1.1 改为 observation cut 之后的固定 non-root read-only exec extraction。collector 退出前不
   exec；post-cut `cat` 本身进入 TCB、command receipts 与限制，不被描述成绝对无干扰读取。
4. 下一批必须是全新 precommit/hash/anchor。A–E 只支持这些运行时判断，不能支持 detector、T
   chance、prefix qualification 或任何 A1–A5 比较结论。
5. F 只支持 V1.3 runner/evidence path 的 structural closure。旧 evaluator 的拒绝说明 schema/profile
   独立实现没有被 runner 绿灯覆盖；F 不具 formal 人口，也没有执行所选完整 profile，因此仍不能
   支持 detector sensitivity、T equivalence、prefix qualification 或任何 treatment 比较。
