# Wave 016 artifact 状态

日期：2026-07-30

| Run | 状态 | 用途 |
|---|---|---|
| `run-5e3bb50c02a545ed8594c982b5f54c90` | `ROOT-ACCEPTED / SCOPED LOCAL-DIGITAL` | 唯一冻结正式验收 artifact |
| `run-ee4c7f1025c4487a9034e91a80609525` | `HISTORICAL_PRE_ROOT_FIX / NOT ROOT-ACCEPTED` | 仅保留演化与缺陷追踪 |

旧 run 生成于 endpoint key binding、真实历史 decoy ledger 和 capability-native freshness
修正之前，也没有独立 ROOT evaluator。它的原始文件不删除，但不得支持 Wave 016 的正式
artifact 接受结论。

新 run 的冻结哈希为：

`3059bdc91c09bd1e71a5f6827453bbc157290f45967bdffa7f589e6e856b2abe`

接受范围只包括本地数字 E3A/E3B paired-world solution；不包括法律 Authority、物理
Effect、外部 PKI、生产可靠性、relation formation 或协议整体晋升。
