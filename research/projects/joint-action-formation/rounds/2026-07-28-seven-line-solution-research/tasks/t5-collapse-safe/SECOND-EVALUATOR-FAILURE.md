# T5 V2 evaluator failure

状态：`INVALIDATED / REPLACED_BY_V3`  
日期：2026-07-28

V2 修复了 V1 的零动作标签伪成功，但第二轮独立攻击仍发现两个承重漏洞。

## 反例一：adapter 完全靠自报

只把正例 fixture 的 adapter 名称改成
`STATEFUL-AUTHORITATIVE-SHADOW-LEDGER-LEAKS-PII-AND-RETRIES`，同时继续自报
`authoritative=false`、`writes_state=false`、`caches_state=false` 和零成本，仍得到
`6/6 PASS`。

这个反例不证明名称描述的恶意行为真的发生；它证明 evaluator 没有执行或绑定任何 adapter
artifact，因此无法区分诚实 adapter 与撒谎候选。V2 对 adapter 的 R2/R3/R4/R6 是
attestation，不是 evidence。

## 反例二：注入失败被错误当作实际终态

把 `CREATE_ORDER` 的 seat 输入改错后，平台在第三步已经得到
`valid=false / order_status=INVALID`。V2 仍把四次 failure run 分别报告为注入的
`ORDER_REJECTED / PAYMENT_FAILED / PROVISIONING_FAILED / CANCELLED`，使 R5 继续通过。

原因是 simulator 在失败没有真实发生时也返回注入标签；声明的 recovery handler 也没有被
执行。

## V3 必须改变什么

- LIGHTWEIGHT_ADAPTER 必须绑定实际 artifact hash；
- evaluator 只执行受限 JSON transducer，不信任自报权威、存储、缓存、披露和成本；
- 披露和成本从实际 adapter trace 推导；
- failure 只有在有效前置链到达相应状态时才成为终态；
- invalid predecessor 返回 `INVALID_OPERATION`；
- recovery handler 必须在 evaluator 中实际解释执行，并证明 readback 后停止、无 retry 和
  无额外副作用。

V2 当时冻结的关键哈希：

- `evaluator.py`: `e37da3ba01edbca887cf0157a4381a4f834fbb03001b4cfda2570c8d3225608c`
- `platform_simulator.py`: `2682dd1d5c7362498f6b804bdbbbd27aa8ba605d7b9b8af5f672c64ecf4d1894`
- `submission.schema.json`: `1e15e55e1cc632d1b2c0ba5162ae10ede7f1ec78151972fb0fcdfb92174aeb3e`
- `fixtures/stateless-adapter.json`: `26748105d9eea6e8b0c36fd95b16d8140b3f7fead7e49e6d98b62c15e9f7d769`

保留这个失败是为了阻止后续再次把候选声明、命名或 schema 合法性当作 adapter 行为证据。
