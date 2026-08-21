# Raw evidence

实现身份：`G7_INTERNAL_AGENT_B`。

- `run-traces.json`：第二轮 `runner.py` 生成的 process/state/byte-separated line-local
  evidence，包括 owner/target/migration/fence PID、state path、传输 bytes、攻击 readback
  与精确 G7 integration fragment；不再含首轮合同形状。
- `red-history.json`：首次 false-green、冻结敌对红灯、expected-red negative control 与
  post-repair test-contract drift。最终绿灯不得覆盖这些历史。

这里都是本地合成记录，不是生产日志、真人决策或真实供电 Effect。
