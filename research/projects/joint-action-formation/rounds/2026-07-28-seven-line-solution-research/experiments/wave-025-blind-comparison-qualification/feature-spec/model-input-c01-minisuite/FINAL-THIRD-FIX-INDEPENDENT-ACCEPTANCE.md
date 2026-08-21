# C01 minisuite V3 第三轮最终独立窄验收

> 审查对象：V3 六份 canonical artifacts、hash-bound worker、capability receipts、第三轮攻击回归  
> 审查方式：读取 `THIRD-FIX-AUDIT.md` 但不继承其结论；独立重跑运行时 inventory、read/write set、
> full-label probe、递归绕过、outer seal、12 个 binding 攻击、旧 row oracle 与 metadata-only 反例  
> 最终裁决：`ACCEPT_SCOPED_C01_MINISUITE`  
> 精确威胁模型：仅接受“受信任 outer controller + 当前 hash-bound Python worker + Python audit hook
> 所观测的 closed read/write set”。不是独立 UID、内核 sandbox、恶意同 UID 防护或密码学不可篡改。

## 1. 裁决

V2 被拒绝的两项内部 blocker 在 V3 当前 scoped threat model 下已经关闭：

1. freeze worker 的正常 capability root 不再包含 full labels、membership 或 workspace；实际运行
   root mode 为 `0700`，只 stage 三份输入和 worker，Python audit hook 拒绝 workspace full-label
   absolute path，8/8 receipts 的实际 data read/write set一致；
2. V2 的公开 `(case, phase, slot)` row-ID oracle 已被一次性 CSPRNG membership 取代。旧 oracle 对
   640 个 row ID 的命中为 `0/640`；移除 intended predictor values 后，P3/P7 的三个可执行 family
   calibration/holdout BA 都是 0.5，metadata不能救回分类。

同时，递归 schema、outer expected seal、六类 source binding、F4 unavailable、两阶段 stable、F1 OOV
和 P2 conditional 边界均通过独立攻击。

因此可以接受的是：

> 在固定合成 fixtures、受信任 outer controller 与受信任 hash-bound Python worker 条件下，V3
> 是一个可重建、可审计、不会读取 holdout labels来选择规则的 scoped synthetic minisuite；它能
> 比较 F1/F2/F3 的局部机制并诚实保留 F4 Unknown。

不能接受或推导的是：

| 外层判断 | 状态 |
|---|---|
| actual D0 sensitivity | `UNKNOWN / NOT_RUN` |
| actual D1 sensitivity 与 cross-phase premise | `UNKNOWN / NOT_RUN / NOT_PUBLICLY_BOUND` |
| 完整 C01/F4 机器语义 | `UNKNOWN`，F4仍 unavailable |
| `MODEL-INPUT-V2S` canon | `NOT_A_CANDIDATE / NOT_ADOPTED` |
| G | `NOT_RUN / NOT_UNLOCKED` |
| 3200 formal | `NOT_RUN / NOT_AUTHORIZED_BY_THIS_RESULT` |

## 2. 0700 capability root、inventory 与 full-label probe

### 2.1 独立运行时观察

在一次真实 freeze invocation 外围观察 child 启动瞬间的 root：

```text
root mode = 0700
inventory =
  calibration-join.json  0400
  case.json              0400
  contract.json          0400
  worker.py              0500
```

P1 本次实际 bytes 分别为 2,261、12,445、3,200、67,387。其他 case 只改变 `case.json` 与 join
内容/长度，不改变文件集合和 mode。

检查当前 `FROZEN-SELECTIONS` 的全部 8 个 freeze receipts：初始文件名集合均精确为上述四项，
worker SHA 均为：

```text
64341a21f2b53c467d45cf8ee794552f969a083383fcdb09782d901d46ca95a7
```

它与 `RESULTS.implementation_bindings.generator_sha256` 及当前 generator bytes完全一致。

### 2.2 实际 read/write set

8/8 freeze child 的 capability data read set 都精确为：

```text
$CAP/calibration-join.json
$CAP/case.json
$CAP/contract.json
```

write set都精确为：

```text
$CAP/frozen-package.output.json
```

8/8 score child 的 inventory 是 `worker.py`、`contract.json`、`frozen-package.json`、
`holdout-join.json`；data read set精确为这三份 JSON，write set精确为
`$CAP/scored-case.output.json`。score root 没有 raw feature case。

receipt所称“actual set”只包括 audit hook覆盖并记录的 Python filesystem data operations；Python
启动、标准库和允许的系统 runtime read不在 `$CAP` set 内。这个限定与声明的 trusted-worker
threat model一致，不应改写成完整 syscall trace。

### 2.3 absolute-path probe

每个 worker在读取任务文件前安装 audit hook，随后实际 probe当前 workspace的 full-label absolute
path。16 个 freeze/score receipts均满足：

```text
full_labels_artifact_probe_blocked = true
denied_external_read_events =
  $EXTERNAL_SHA256/704c455555513742dfe4aeb24164437b8a1f3614ed264a4ef83f1067bc1b4672
```

独立重算确认：

- 上述 path digest 等于当前 `CASES-LABELS.candidate.json` absolute path的 SHA-256；
- receipt的 forbidden artifact hash 等于当前 full-label bytes hash
  `7a556dc139b24db35e1eeff3fb344e33dcc95cafa98c0b7567d5449d950b2e0d`；
- full labels不在初始 inventory。

V2 的“同权限普通 subprocess能直接读 labels”在当前**受信任 Python worker + audit hook**执行路径中
已被阻断。

## 3. 递归 closed schema 攻击

独立向 freeze staged case 注入：

1. `case.holdout_labels`；
2. `case.rows[0].metadata.role`；
3. `case.rows[0].categories[0].metadata`。

三项均在 worker中 fail closed。case、row、category、numeric/value与 join都检查 exact keys，并递归
拒绝 label-like key；V2 的“只闭顶层”已关闭。

独立向 score frozen package注入：

1. top-level `feature_rows`，并重算变异 package的新 SHA；
2. F2 dynamic `selected_rule.mapping.holdout_labels`，并重算 package SHA。

第一项通过 transport exact-byte binding 后被 package exact-key schema拒绝；第二项被递归
label-like key检查拒绝。也就是说，新 hash不能把一个 schema外 payload变成合法 package。

这不表示 dynamic mapping 的合法 state key集合已经被全局枚举；它只证明当前 scoped rule schema、
内部 rule hash、递归 label-key guard和 outer package seal共同关闭了本轮指定的 metadata/labels绕过。

## 4. outer expected seal

独立区分了两类攻击：

### 4.1 旧 seal + 变异 bytes

冻结 P1 package 后，由 outer receipt取得先验 exact-byte seal；只改 package `description`，仍向 score
提供旧 seal。worker在 JSON parse/score前以 `exact-byte binding mismatch` 拒绝。

### 4.2 新 hash + 非法 schema

给 package新增 `feature_rows`，攻击者同步计算变异后的新 SHA并作为 expected transport binding。
exact-byte检查通过，但递归 frozen-package schema拒绝。

因此 self-reported `package + hash` 的 V2缺口已关闭。这里的“outer seal”依赖受信任 controller先验
保存 freeze output hash；若 controller自己决定同时替换 package和 expected hash，seal不提供防护。
这正是 scoped threat model边界，不是本轮失败。

## 5. 六类 binding 的 12 个攻击

分别对下列六项执行全零与错误非零 SHA-256：

| phase | binding | zero | wrong nonzero |
|---|---|---|---|
| freeze | `contract_sha256` | rejected | exact-byte mismatch |
| freeze | `case_sha256` | rejected | exact-byte mismatch |
| freeze | `calibration_join_sha256` | rejected | exact-byte mismatch |
| score | `contract_sha256` | rejected | exact-byte mismatch |
| score | `frozen_package_sha256` | rejected | exact-byte mismatch |
| score | `holdout_join_sha256` | rejected | exact-byte mismatch |

结果为 `12/12 fail closed`。全零在 outer admission被拒；格式正确但错误的非零值进入 worker后与
staged exact bytes不符而失败。worker还比较 contract content与当前 `build_contract()`，并在 score
核对 frozen package内部 contract binding。

V2 中“contract hash只是未消费的允许键”已经关闭。

## 6. V2 row oracle 与 metadata-only 反例

### 6.1 旧 oracle

重放旧算法：对 8 cases × 2 phases × 40 slots 生成：

```text
sha256("WAVE025_C01_OPAQUE_ROW_V2", case_id, phase, slot)[:24]
```

与 V3 membership 的交集为 `0/640`。当前公开 main module也不再导出 `opaque_row_id` 或
`label_assignments`。V3 membership IDs来自一次性 OS CSPRNG；seed、slot号及反向映射未保留。

这个结果否定的是已知 V2 枚举路径，不是对 96-bit random ID作无条件密码学安全声明。

### 6.2 metadata-only

对 P3/P7 分别清空每一行的 `categories` 与 `numerics`，保留 row ID、case、phase和 membership
metadata。独立结果对 F1/F2/F3逐项都是：

```text
calibration balanced accuracy = 0.5
holdout balanced accuracy = 0.5
selected_rule = null
stable = false
```

因此 P3/P7 的负结果没有被 row metadata暗中救回。它不否定 P1/P4/P5 中人为设计的 intended
predictor signal；正控本来就要求其 predictor与 synthetic class相关。

## 7. 继承语义与来源边界

### 7.1 F4

P6/F4 仍为：

```text
availability = REJECTED_UNDERDETERMINED_NOT_EXECUTED
candidate_count_generated = 0
selected_rule = null
failure_reason = RULE_FAMILY_SPEC_UNDERDETERMINED_NO_EXECUTION
```

没有恢复 V1 的 Boolean lookup。scoped acceptance只覆盖 F1/F2/F3及“F4必须保持 Unknown”的行为，
不代表完整 C01 detector已经闭合。

### 7.2 P2 与 actual control

P2继续是 `P2_D1_CONDITIONAL_STABLE_EXACT_ATOM`，premise为：

```text
UNKNOWN_CONDITIONAL_CROSS_PHASE_STABILITY_NOT_EXPRESSED_BY_BOUND_PUBLIC_REGISTRATION
```

`RESULTS` 中 actual D0/D1 都是 `UNKNOWN_NOT_RUN...`。P1仍只是公开 D0设计与理想 stable atom的
合成机制兼容性；P2不再借未绑定 private registry升级公开 D1事实。

## 8. 六份 canonical artifacts、bindings 与 clean tests

`--check` 独立返回：

```text
byte-exact canonical check passed: 6 artifacts
```

当前字节：

| 文件 | bytes | SHA-256 |
|---|---:|---|
| `OPAQUE-MEMBERSHIP.candidate.json` | 19,318 | `7b78a670559e4bab3282d3ed68e78a870cd3d42b6be620c7ac524b9dcb4c1e2f` |
| `CASES-FEATURES.candidate.json` | 95,917 | `ca69b343a6402af58660d5634de9c619424cff2b78b9fc63b9644d4f61d580f7` |
| `CASES-LABELS.candidate.json` | 35,345 | `7a556dc139b24db35e1eeff3fb344e33dcc95cafa98c0b7567d5449d950b2e0d` |
| `C01-MINISUITE-CONTRACT.candidate.json` | 3,200 | `ef20eaf74307ea3e224a4fa4ff29d051d2be377245615acb760a535e4619c8c5` |
| `FROZEN-SELECTIONS.candidate.json` | 332,561 | `acc5fa8c65d9f24f26bb8152bbe74fa0d3948e736dd419ea712e13a7c5d53c79` |
| `RESULTS.candidate.json` | 55,162 | `7974ab22da00bde913ab7482606aa1eb9d1b76777acd38eaf1678e2fc002599a` |

独立核对：`RESULTS` 对上述前五份输入 artifact、generator、initializer、tests、README及两个公开
control sources的 binding全部非零且与当前 exact bytes相符；8 个 freeze receipts的 staged worker
hash也都等于 generator binding。

clean current snapshot执行：

```text
PYTHONPYCACHEPREFIX=/tmp/wave025-c01-v3-independent-final-pycache \
python3 -m pytest -q feature-spec/tests \
  feature-spec/collector-v1.1-candidate/tests \
  feature-spec/model-input-c01-minisuite/tests --disable-warnings
=> 166 passed in 59.14s
```

测试前后 membership、五个生成 artifacts、generator、initializer、tests、README和
`THIRD-FIX-AUDIT.md` hashes完全不变。测试数和 canonical green只支持本报告所列内部语义/接口，
不支持现实功效。

## 9. 接受边界与不得升级的表述

`ACCEPT_SCOPED_C01_MINISUITE` 的必要限定必须和结论同时保留：

- outer controller受信任，并先验保存/传递 expected hashes；
- worker exact bytes由 receipt与 `RESULTS` hash绑定，worker Python代码受信任；
- Python audit hook用于观察和拒绝该 worker的普通 filesystem访问；
- capability root的临时目录、inventory和read/write receipt在当前运行中可复核；
- 不覆盖 worker通过 native syscall、`ctypes`、新 subprocess、继承 fd或其他绕过 audit hook的恶意行为；
- 不覆盖同 UID 恶意进程抢读/改写临时目录、恶意 controller同步替换 bytes与expected seal；
- 不是独立 UID、mount namespace、seatbelt/container/kernel sandbox、签名或append-only外部账本；
- receipt与mode/hash能发现当前普通漂移，不是对本机强对手的密码学不可篡改证明。

在这些边界内，本 minisuite不再因 V1/V2 的五项内部 blocker被拒绝；可以作为后续 C01语义选择的
局部研究工具。超出这些边界，尤其是 actual D0/D1、完整 F4/C01、MODEL-INPUT、G与3200，仍须由
各自独立 gate与证据关闭。
