# Wave 016 ROOT 独立验收

日期：2026-07-30  
状态：`ACCEPTED_SCOPED_LOCAL_DIGITAL_E3_PAIR / NO FORMAL RESEARCH PROMOTION`

## 接受对象

唯一接受的冻结运行：

`artifacts/run-5e3bb50c02a545ed8594c982b5f54c90`

冻结哈希：

`3059bdc91c09bd1e71a5f6827453bbc157290f45967bdffa7f589e6e856b2abe`

正式验收文件：

- `ROOT-FREEZE.json`：原始 JSON 文件哈希与 SQLite 逻辑快照哈希；
- `ROOT-INDEPENDENT-ACCEPTANCE.json`：独立验收结论、逐项检查和未证明范围；
- `ROOT-FROZEN-SQLITE/`：四个由运行 DB（含已提交 WAL 页）备份得到的 standalone
  `DELETE`-journal SQLite；每个文件同时冻结物理 SHA-256 与逻辑快照 SHA-256；
- `evaluator.py`：不导入 `pair_runtime` 的独立 evaluator。

`pair-evaluation.json` 和 `result.json` 被明确视为不可信运行方总结。它们被纳入冻结文件哈希，
但不参与通过/拒绝判断。

## 独立重算结果

ROOT evaluator 直接从两个 blind launch receipt、arm/broker transcript、Ed25519 记录和四个
standalone SQLite 冻结账本重算。原运行目录中的 DB/WAL/SHM 只作 provenance，不作为接受
truth source：

- 两个真实 spawn arm 的 startup view bytes 完全相同；
- submit、`OUTCOME_UNCONFIRMED`、exact status query 组成的 pre-readback prefix 完全相同；
- 首个公开差异位于 transcript index 3，且只能是 exact Target status response；
- 所有 Target status、freshness 与 decoy wrapper 均由该 world 冻结的 endpoint key 签名；
- world-a 的签名 status、账本 receipt/readback、commit event 与最终 head 指向同一个 commit；
- world-a 没有 freshness/retry，exact target mutation count 为 1；
- world-b 的签名 negative 覆盖 genesis 至 observed version 0，且 occurrence 为空；
- world-b 在 retry 前取得未消费、exact target/actor/operation/state 的 capability freshness；
- world-b retry 保留 request/operation identity 与 negative-head 前提，最终 exact target
  mutation count 为 1；
- C8 decoy 不匹配 run/world/object/target/operation，并可追溯到独立历史账本中的真实
  commit、receipt 与 readback；
- ledger receipt/readback 的内容 hash、HMAC、SQLite 存储身份和 capability 消费关系均有效。

两个世界各自的 current target ledger 只有一项 target、一个 request、一个 receipt、一个
readback、一个 capability 和一个 commit event；未以其他 target mutation 偷换总数。

## 攻击验收

独立攻击测试覆盖并拒绝：

1. current-head coverage 不完整但声称 `NOT_COMMITTED`，即使伪记录重新合法签名；
2. capability 已消费却声称 `CURRENT`，即使伪记录重新合法签名；
3. decoy wrapper 存在但历史账本没有真实 commit；
4. Target response 被替换为另一个自签 key；
5. safe retry 出现在 freshness 之前；
6. exact target 出现第二个 commit event；
7. 两个 world 的 pre-readback prefix 出现任意差异。
8. 任一冻结 DB 回到 WAL mode、出现 WAL/SHM companion，或不再是 standalone
   `DELETE`-journal 文件。

测试结果：

- Wave 016 全部测试：`15 passed`；
- 其中独立 evaluator 与攻击测试：`9 passed`；
- Wave 015 visibility/Target ledger 回归：`21 passed`。

## 接受结论

本轮只接受以下有界结论：

> 在冻结的本地数字世界和合作式进程边界内，成熟组合  
> `Target operation ledger + exact signed status/readback + one-shot capability +  
> capability freshness + idempotent retry`  
> 能够区分 ACK 丢失后的“已经提交”和“尚未提交”，并分别执行 no-replay reconcile 与
> freshness-gated safe retry；E3A/E3B 各自只产生一个 exact digital target mutation。

这是现有技术组合对 E3A/E3B 局部问题的正向解题结果，不要求额外“通爻独占增量”。

## 未证明

本验收不证明：

- 真实电路的物理 Effect 或 46 个物理样本；
- capability 对应法律 Authority，或参与方具有独立 Principal 身份；
- endpoint key 已由外部 PKI、硬件根或现实主体签名绑定；
- 对拥有同一目录写权限的恶意本机进程具有防篡改能力；
- 生产可靠性、跨域迁移性或长期漂移下的有效性；
- relation formation、协议整体有效性或任何正式机制晋升。

当前 endpoint key binding 是 evaluator-private broker artifact 内的冻结信任根。它足以拒绝
相对于该冻结根的 response key 替换，但同权限攻击者仍可同时改写响应、信任根和 artifact。
冻结哈希也只是本地内容寻址，不是外部 append-only 或签名锚。

## 历史运行

旧 `run-ee4c7f1025c4487a9034e91a80609525` 已降级为
`HISTORICAL_PRE_ROOT_FIX / NOT ROOT-ACCEPTED`。它不得被引用为本轮正式 artifact 验收证据。
具体状态见 `artifacts/STATUS.md`。
