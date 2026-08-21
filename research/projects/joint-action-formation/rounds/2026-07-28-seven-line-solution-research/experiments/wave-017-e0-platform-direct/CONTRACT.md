# Wave 017 — E0 Platform Direct 正向基线合同

状态：`ROOT-AUDITED LOCAL SYNTHETIC BASELINE`

正式接受只认 `artifacts/ROOT-ACCEPTANCE.json` 当前绑定的 V2 pair。早期仅冻结 task、以
内存常量报告 external zero 的 batch 是保留的历史运行，不构成本合同的正式证据。

## 1. 研究问题

本线不研究怎样创造新关系，而是主动检验最简单的现有正解：

> Venue 已经合法拥有合格资源、target、调度平台和全部必要 direct Authority 时，平台原生
> policy/IAM、内部资源锁、TargetOperationLedger 和 readback 能否在不做外部 discovery、
> relation formation、delegation 或 transfer 的情况下完成 exact CE-001 task？

如果能够完整解决，应登记为通爻的正向有界方案，不得因没有新机制而降级。

## 2. exact task

冻结任务为：

- `Q@v1`；
- `VenueV:CircuitC7`；
- deadline `T0 + 90min`；
- 连续不少于 45 分钟、`3kW ± 5%`；
- safety/noise 均满足；
- 不给其他 circuit 送电；
- exact target readback；
- requester 与 venue Acceptance 由 lawful unified platform-native closure 表示；
- Venue 自有 resource/target，不发生外部 transfer。

合成 target state 保存 `minute=0..45` 共 46 个 power/safety/noise sample。

## 3. world 与 Authority

正控环境是：

```text
authority_stratum = U / LAWFULLY_UNIFIED
principal         = VenueV
platform          = VenueV:NativeOperationsPlatform
resource          = VenueV:Battery:B7
target            = VenueV:CircuitC7
```

O_V 以 Ed25519 签发 exact operation grant，绑定 platform、resource、target、Q、operation、
issued/expiry。platform 只有在 signature、digest、scope、freshness 和
`LAWFULLY_UNIFIED_DIRECT` 全部满足时才可继续。

V2 pair 在两臂运行前冻结并哈希同一个输入，至少包括 task、initial target state、
operation/request、resource、target ledger id、native interface、Venue Authority 公钥和
platform service 公钥。两个 spawned run 读取同一 frozen preimage；counterexample 只替换
带同一 grant subject 的 signed direct-Authority treatment（`PRESENT → REMOVED`）。
Authority 状态必须从 frozen Venue 公钥和 signed grant 重算，不得读取
`private_world_reveal` 作为事实。

counterexample 必须：

- `POLICY_DENIED`；
- 不锁 resource；
- 不签发 target capability；
- Target version 保持 0；
- 无 Effect；
- 不以失败为由外部 discovery、formation 或 transfer。

## 4. blind-spawn arm

arm 使用真实 `multiprocessing.spawn` child，只收到：

- opaque run/request/operation identifiers；
- exact public task；
- signed Venue Authority grant；
- 单一 `PLATFORM_PROVISION_EXACT_TASK` native interface。

arm 不收到 private world reveal、expected outcome 或 counterexample label。Authority grant
的 ALLOW/DENY 是现实合法 observation，不是 grader label。arm 不实现 case-specific
decision tree，只向平台提交一次 exact native request。

Platform service 是另一个独立 spawned process。arm 与 service 的 PID 必须不同。
独立 evaluator 还必须重建 start payload hash，要求 visible field schema 精确、两臂使用相同
opaque run id、arm/service/controller PID 互异、两侧 start method 均为 `spawn`，并从 service
request 与 event DB 双重确认只有一次 native call。arm 进入同一个由 pair id 派生、启动时为空
的中性 temp cwd；argv/process name 固定为 `opaque-native-worker`。arm 的 input schema、run id
和 interface 不含 E0、Wave 017 或 platform-direct 候选身份。

arm 与 service 的 inherited environment 在 spawn 时都先缩到固定最小键值映射，并把完整安全
映射写入 startup receipt；独立 evaluator 逐键逐值重建，不信任 controller 的
“labels absent”布尔值。Service 可以知道自己的平台角色；arm 除 exact task、signed Authority
与 generic native response 外不得获得 applicability、removal-counterexample、expected
outcome 或 result oracle。

## 5. 平台原生路径

正控只允许：

```text
one platform-native request
→ policy/IAM verifies direct Authority
→ internal Venue-owned resource lock
→ exact one-shot TargetOperationLedger capability
→ expected-version/CAS target COMMIT
→ authenticated target readback
→ NO_EXTERNAL_TRANSFER_DUE
```

以下计数必须为零：

```text
external discovery calls
external relation events
external delegation events
external transfer count
model calls
human coordination minutes
```

四项 external zero 不得由 evaluator 常量产生。platform SQLite 必须保存每个 native
request、policy decision、resource lock、target commit/readback、role Acceptance 和
finality 的 event row；external event type 也属于同一 registry。正式 evaluator 从冻结后的
SQLite events 表重新计数，并逐项核对 service-log payload hash。

这个 event ledger 证明的是本 platform service 的已登记事件面没有 external event。它不证明
OS 级 network noninterference，也不证明宿主机上不存在未受本 runner 观察的其他进程活动。

内部 policy check、resource lock、target capability 和 target commit 不得被重命名为外部
relation formation。

## 6. Target mutation 与因果归因

平台复用 Wave 015 `TargetOperationLedger`：

- ledger 是本合成 digital target 的唯一 mutation truth owner；
- expected-version/CAS；
- exact actor/target/state one-shot capability；
- target mutation、capability consumption、commit provenance 与 receipt 原子落盘；
- readback 绑定 exact receipt/commit；
- receipt 的 actor 必须是平台。

只有 `COMMITTED + mutation_applied=true + attached readback + exact target state`，且
Target DB 的 commit actor、platform event row 与 frozen request 相互一致时，才允许
`EffectAttributableToPlatform=true`。该字段的固定 scope 是：

```text
DIRECT_DIGITAL_TARGET_COMMIT_ONLY
```

它不表示真实电力已经输出，也不对完整任务的物理因果效果作归因。

## 7. Finality

正控 finality 必须显式为：

```text
decision = NO_EXTERNAL_TRANSFER_DUE
reason   = VENUE_OWNS_PLATFORM_RESOURCE_AND_TARGET
external_transfer_count = 0
```

这不是漏做 Settlement；它表示当前 U world 内不存在外部 beneficiary obligation 或外部
transfer。Removal counterexample 同样不得发生 transfer，但不能生成成功 finality。

## 8. evaluator coordinates

`independent_evaluator.py` 不 import `platform_direct.py` 或 Wave 015 实现。它从 artifact、
frozen Venue/platform 公钥和两个 standalone SQLite 文件独立重算：

```text
TaskOutcomeSatisfied
CorrectResolution
SafeHandling
UnnecessaryFormation
EffectAttributableToPlatform
ExternalDiscoveryCalls
ExternalRelationEvents
ExternalDelegationEvents
ExternalTransferCount
TargetVersion
ResourceLocked
```

Target receipt/readback 的 digest、HMAC 与 SQLite stored identity，platform Acceptance /
finality 的 Ed25519 signature，resource row、event rows、DB integrity、journal mode 及全部
文件 hash 都必须通过。两个 DB 必须 checkpoint 后处于 `journal_mode=DELETE`；正式证据不能
依赖 WAL。

正控要求：

```text
TaskOutcomeSatisfied = true
CorrectResolution = true
SafeHandling = true
UnnecessaryFormation = false
EffectAttributableToPlatform = true
TargetVersion = 1
ResourceLocked = true
all external counts = 0
```

Authority removal 要求：

```text
TaskOutcomeSatisfied = false
CorrectResolution = true
SafeHandling = true
UnnecessaryFormation = false
EffectAttributableToPlatform = false
TargetVersion = 0
ResourceLocked = false
all external counts = 0
```

## 9. 成本面

至少记录：

- wall time 与 child process count；
- platform native calls；
- policy checks；
- internal resource lock operations；
- target mutation attempts；
- model calls、human minutes；
- external discovery/relation/delegation/transfer；
- cold integration cost；
- repeat path；
- maintenance cost 是否实际测量。

一次本地合成运行不能证明真实采购、停更、锁定、迁移、漏洞或长期维护成本。

## 10. 正向登记边界

当正控、removal counterexample、blindness、Target receipt/readback 和 evaluator attacks 全部
通过，且 `ROOT-ACCEPTANCE.json` 对 summary、两臂 artifact、四个 DB、实现、独立 evaluator
和合同的字节 hash 全部冻结时，本线允许登记：

```text
E0_PLATFORM_DIRECT_EXISTING_COMPOSITION = POSITIVE_SCOPED_SOLUTION
UNNECESSARY_RELATION_FORMATION_FOR_E0 = REJECTED
NOVEL_MECHANISM_NECESSITY_FOR_E0 = CLOSED
```

其解题价值属于通爻方案，即使全部组件都是成熟现有技术。

这不说明：

- 没有 direct Authority 时平台仍可行动；
- E1–E6 已解决；
- 真实电路或真人 Acceptance 已发生；
- 两个 role Acceptance 来自两个独立现实主体；在 U world 中它们由同一 Venue Principal
  通过两个平台角色签署；
- A0 在 P / PLURAL_INDEPENDENT 中适用；
- OS 级不存在任何外部联网或旁路；
- 能抵抗拥有同目录写权限的恶意 controller；本地 HMAC key 与签名 private key 都由受信
  controller 建立，ROOT 证明冻结后的自洽与普通改写可检测性，不是外部不可伪造锚；
- platform direct 普遍优于 A1–A5；
- CE-001 全 family 或 V1/V2 已解决。
