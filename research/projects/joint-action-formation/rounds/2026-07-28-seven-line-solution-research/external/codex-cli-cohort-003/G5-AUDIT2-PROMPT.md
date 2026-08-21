# G5 第二轮独立边界复核

读取 `COMMON.md`、`G5-PROMPT.md`、`G5-FIX-PROMPT.md`、`G5-fix-final.md`、
`ROOT-LIVE-AUDIT.md` 与 `g5-authority/`。这是 G5 主线的后续独立红队，不预设实现正确。

在同一 CLI 内实际建立 A/B/C：A 只重建可信 bootstrap、owner ingest、target gate 和
migration 的失效面；B 只负责复跑和最小负例 harness；C 独立寻找 false green。
只可修改本目录 `G5-audit2-final.md`；不得修改实现、测试或其他文件。

重点复核：

- trusted topology/channel/owner keys 是否只是 controller fixture 自证；
- revoke withholding、out-of-order ingest、channel crash/restart、key rotation；
- owner-head/resource-fence namespace transplant；
- target 是否消费 exact current receipt set，还是只认 snapshot summary；
- current snapshot、takeover lease 与 target state 是否可由同一个 controller 同源生成；
- old-source restart 是否真的由不同 process/state path，shared store 是否掩盖迁移；
- duplicate physical Effect、target restart 丢 fence、two concurrent takeover；
- U/D/P topology 是否仅标签不同；
- artifact/PID/source hashes 是否只证明自洽。

实际复跑必要测试和不写实现的内存/临时失效注入，给出 P0/P1、精确行号、可保留能力与
`NOT_RUN` 边界。不得把测试绿灯、PID 数量或签名自洽当现实 Authority。
