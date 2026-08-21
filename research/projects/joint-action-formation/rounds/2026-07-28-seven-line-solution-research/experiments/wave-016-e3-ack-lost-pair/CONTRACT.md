# Wave 016：E3 ACK 丢失双世界可执行合同

日期：2026-07-30  
状态：`EXECUTABLE LOCAL DIGITAL EXPERIMENT / NO FORMAL PROMOTION`

## 研究问题

在 arm 的启动输入与 ACK 丢失后的可见前缀完全相同时，现有成熟机制组合能否仅凭
Target 的 exact authoritative status/readback，正确区分：

- 第一次 submit 已提交，因此只 reconcile、不得 replay；
- 第一次 submit 未提交，因此在 current capability 状态复核后 safe retry？

本轮不寻找“通爻独占增量”。若
`Target operation ledger + exact signed status/readback + one-shot capability +
idempotent retry` 已经完整解决，这就是正向解题结果。

## 两个真实运行世界

两个 arm 均由 Wave 015 `BlindProcessLauncher` 以真实 `multiprocessing spawn` 启动，并接收
同一个 `ArmViewFactory` 产出的、逐字节相同的 startup view。固定 Queue IPC 只承载 broker
请求/响应。

共同公开前缀包括：

1. startup view；
2. exact `SUBMIT` request；
3. 相同 `OUTCOME_UNCONFIRMED` response；
4. 相同 exact `STATUS/READBACK` query。

第一个公开差异只能是 Target 对该 exact query 的签名响应。

### world-a

broker 在返回 `OUTCOME_UNCONFIRMED` 前，已通过 `TargetOperationLedger.apply` 原子提交一次。
exact status 返回 `COMMITTED`、原 receipt 与 attached readback。arm 必须终止重试并返回：

`RECOVERED_EXISTING_EFFECT_NO_REPLAY`

### world-b

第一次 submit 未调用账本 mutation。exact status 在 version 0 的 current head 上签出
`NOT_COMMITTED`。响应同时携带一个由独立 historical Target ledger 实际 commit/readback
支持的签名 decoy，但它的 run/world/object/target/operation 均不匹配，不能满足 exact
query。arm 排除 decoy、取得签名的 capability freshness，再用同一 semantic
request/operation 安全重试，返回：

`RECOVERED_NO_EFFECT_SAFE_RETRY`

## 唯一 mutation truth

`TargetOperationLedger` 是两个世界唯一的 durable digital mutation path。每个世界的
`commit_events` 最终都必须恰好为 1：

- world-a：第一次 submit mutation = 1，recovery mutation = 0；
- world-b：第一次 submit mutation = 0，safe retry mutation = 1。

历史 decoy 是独立 historical ledger 的实际 C8 commit/readback，再由当前固定 Target
endpoint 签出 query projection；它不写入当前 C7 world ledger，因此不能借 decoy 增加
当前任务 mutation。

## 验收

- 两个实际 blind-spawn receipt 均存在；
- startup view bytes 相同；
- readback response 之前的三条 transcript event 完全相同；
- transcript 首个差异索引为 exact Target status response；
- world-a 没有 safe retry；
- world-b 在签名 exact negative 与 capability freshness 之前没有 retry；
- decoy 被 object/target/operation/world 精确排除；
- 两个账本 mutation count 均为 1，最终 version 均为 1；
- receipt/readback 由账本在父进程重新验证；
- 原始 arm/broker transcript、launch receipt、ledger audit 与 pair evaluation 落盘。

## 证据边界

本轮只证明一个本地数字状态机组合在冻结条件下可执行，并能避免 ACK-lost 的固定
retry/no-retry 两类错误。它不证明：

- 真实电路产生了物理 Effect 或 46 个物理样本；
- capability 对应法律 Authority；
- Target key 已由外部 PKI 绑定到现实主体；
- 同 OS user 下抵抗恶意进程；
- 生产可靠性、跨域泛化或通爻形成机制成立。

Target 状态封装使用 Ed25519。Arm 在本实验中依赖固定 broker endpoint；parent evaluator
还要求所有 Target status、capability freshness 和 decoy projection 使用该 endpoint
预注册 public key。它测试签名完整性与 exact query/current-head 绑定，不宣称完成外部
PKI 或现实身份认证。

## 运行

```bash
python3 run.py
pytest -q
```

每次运行在 `artifacts/run-<opaque>/` 保留独立原始证据，不覆盖历史运行。
