# C01 minisuite V3 third-fix audit

> 日期：2026-08-01  
> 状态：`FIVE FINAL-REVIEW ATTACKS REGRESSED / SAME REVIEWER RECHECK REQUIRED`  
> 边界：`NOT MODEL-INPUT CANON / ACTUAL D0 D1 UNKNOWN / F4 UNAVAILABLE / G AND 3200 NOT RUN`

## 1. 为什么需要第三轮

`FINAL-INDEPENDENT-ACCEPTANCE.md` 接受了 V2 的 F4 不补义、两阶段 stable、F1 OOV 与 P2 来源边界，
但正确拒绝了 scoped acceptance：两个普通 subprocess 仍共享工作区读取能力；case/frozen package
只做顶层 closure；package 与其 self-reported hash可同步替换；contract hash未消费；公开
`(case,phase,slot)` 算法可恢复 640/640 labels。

V3 没有把“进程拆分”继续包装成能力隔离，而是分别改变可读 surface、admission、seal和 source。

## 2. 五项修复与攻击回归

### A1. Freeze 最小 capability root 与 actual read-set

每个 case 创建独立 mode `0700` 临时 root，只含：

```text
worker.py                0500
contract.json            0400
case.json                0400
calibration-join.json    0400
```

full `CASES-LABELS`、membership、holdout join、其他 case 和 workspace材料均不复制。worker用
`python3 -I -S -B` 和最小 environment启动。Python audit hook在读取任务文件前安装，允许系统 runtime
与 capability root，拒绝其他 filesystem read。

8/8 freeze receipts的实际 `$CAP` data read-set都精确为：

```text
$CAP/calibration-join.json
$CAP/case.json
$CAP/contract.json
```

write-set都只含 `$CAP/frozen-package.output.json`。每个 worker还实际尝试读取工作区 full-label path；
8/8得到 `PermissionError`，receipt中的 denied path digest与 outer重算的 path digest一致，full-label
artifact bytes hash也由outer绑定。

这是一项针对**受信任 Python worker**的可审计 runtime capability guard。它不是独立 UID、内核沙箱，
也不声称抵抗任意 native syscall/恶意 controller；V3不再把普通进程拆分本身当作隔离证据。

回归：`test_freeze_minimal_capability_root_excludes_and_cannot_read_full_labels`。

### A2. Freeze/score 递归 closed

freeze逐层关闭 case、rows、categories、numerics/value和 calibration join，并递归拒绝 label-like key。
以下攻击全部 fail closed：

- `case.holdout_labels`；
- `case.rows[0].metadata.role`；
- 任一 row/category/numeric extra field。

score逐层关闭 frozen package、source bindings、universe、family freezes、metrics、prediction rows、
selected rules、selector/mapping。以下攻击均失败：

- top-level `frozen_package.feature_rows`；
- dynamic rule mapping 深层 `holdout_labels` key；
- 任一未声明 nested field。

回归：

- `test_recursive_freeze_schema_rejects_nested_holdout_labels_and_row_extras`；
- `test_score_recursive_schema_rejects_feature_rows_even_with_matching_mutated_hash`；
- `test_score_rejects_deep_label_like_key_even_inside_dynamic_rule_mapping`。

### A3. Outer exact-byte seal，不再接受 self-reported package hash

freeze worker先写 canonical output。outer wrapper在 worker退出后读取 exact bytes、计算 SHA/length，
并把这个 seal写入 frozen receipt。score的 expected frozen hash通过 wrapper environment传入，不在
package或同一 payload里自报。

两种攻击被分别区分：

1. 变异 package但保留先验 outer seal：在 parse前因 exact-byte mismatch失败；
2. 攻击者按变异 `feature_rows` package重算一个新 hash：可以通过transport hash，但随后被递归
   package schema拒绝。

回归：`test_external_frozen_seal_rejects_synchronized_payload_mutation` 与 feature-rows test。

### A4. 所有实际输入 binding非空且 exact消费

freeze的 contract、case、calibration join，score的 contract、frozen package、holdout join，均要求：

- `[0-9a-f]{64}`；
- 非全零；
- 等于 staged file exact bytes的 SHA-256。

worker还要求 contract content逐字段等于当前 V3 `build_contract()`；frozen package内部必须把同一
contract hash、case hash、universe hash、prediction hash和rule hash闭合。RESULTS再绑定 membership、
features、labels、contract、frozen selections、generator、initializer、tests、README与两个公开
control sources。

三个 freeze source binding逐一用全零和错误非零值攻击：6/6 fail closed。错误 contract不再被忽略。

回归：`test_zero_and_wrong_freeze_source_bindings_all_fail_closed`、
`test_all_result_bindings_are_nonzero_and_exact`。

### A5. 移除 row-ID/label 可枚举同源映射

V3新增一次性 CSPRNG `OPAQUE-MEMBERSHIP`，包含640个固定 opaque row IDs。generation seed、slot号和
row-ID映射没有保存。`CASES-LABELS`是独立 row_id→synthetic class source；正常 build只读取/验证，
不重新生成。

公开 main/initializer中不存在 `opaque_row_id` 或 `label_assignments`。重放V2的
`case+phase+slot 0..39` 枚举得到0/640 membership命中，因而不能再恢复640/640 labels。

这里不声称合成 label是秘密，也不要求移除 intended predictor signal。outer controller本来需要
labels来构造合成正控；边界是其完整 mapping不进入 freeze capability root。把 categories/numerics
全部移除后，P3/P7 的 F1/F2/F3 calibration/holdout BA均精确为0.5、没有 selected rule、stable=false；
row ID/case/phase metadata没有救回负控。

回归：

- `test_legacy_640_of_640_slot_oracle_recovers_zero_membership_ids`；
- `test_metadata_only_cannot_rescue_p3_or_p7_above_chance`；
- `test_feature_fixture_has_independent_membership_binding_and_no_plaintext_classes`。

## 3. 继承的接受项没有倒退

- F4仍为 `REJECTED_UNDERDETERMINED_NOT_EXECUTED`，P6没有 Boolean lookup；
- stable仍要求 calibration与holdout两阶段双类 recall=1；
- F1 unknown token仍只走 selector presence/absence truth table；
- P2仍为 conditional，public D1没有被冒充为已绑定 cross-phase premise；
- P1/F1、P4/F2、P5/F3的合成正结果及P3/P7负结果保持；
- actual D0、actual D1仍为 `UNKNOWN / NOT_RUN`。

## 4. clean snapshot 验证

```text
python3 feature-spec/model-input-c01-minisuite/c01_minisuite.py --check
=> byte-exact canonical check passed: 6 artifacts

PYTHONPYCACHEPREFIX=/tmp/wave025-c01-v3-pycache \
python3 -m pytest -q feature-spec/model-input-c01-minisuite/tests --disable-warnings
=> 16 passed in 3.79s

PYTHONPYCACHEPREFIX=/tmp/wave025-feature-v3-final-pycache \
python3 -m pytest -q feature-spec/tests \
  feature-spec/collector-v1.1-candidate/tests \
  feature-spec/model-input-c01-minisuite/tests --disable-warnings
=> 166 passed in 25.23s

PYTHONPYCACHEPREFIX=/tmp/wave025-c01-v3-pycache \
python3 -m py_compile feature-spec/model-input-c01-minisuite/c01_minisuite.py \
  feature-spec/model-input-c01-minisuite/tests/test_c01_minisuite.py \
  feature-spec/model-input-c01-minisuite/initialize_membership_sources.py
=> exit 0
```

urllib3/LibreSSL warning仍只是环境warning，未支持任何网络/TLS结论。

## 5. V3 最终字节

| 文件 | bytes | SHA-256 |
|---|---:|---|
| `OPAQUE-MEMBERSHIP.candidate.json` | 19,318 | `7b78a670559e4bab3282d3ed68e78a870cd3d42b6be620c7ac524b9dcb4c1e2f` |
| `CASES-FEATURES.candidate.json` | 95,917 | `ca69b343a6402af58660d5634de9c619424cff2b78b9fc63b9644d4f61d580f7` |
| `CASES-LABELS.candidate.json` | 35,345 | `7a556dc139b24db35e1eeff3fb344e33dcc95cafa98c0b7567d5449d950b2e0d` |
| `C01-MINISUITE-CONTRACT.candidate.json` | 3,200 | `ef20eaf74307ea3e224a4fa4ff29d051d2be377245615acb760a535e4619c8c5` |
| `FROZEN-SELECTIONS.candidate.json` | 332,561 | `acc5fa8c65d9f24f26bb8152bbe74fa0d3948e736dd419ea712e13a7c5d53c79` |
| `RESULTS.candidate.json` | 55,162 | `7974ab22da00bde913ab7482606aa1eb9d1b76777acd38eaf1678e2fc002599a` |
| `c01_minisuite.py` | 67,387 | `64341a21f2b53c467d45cf8ee794552f969a083383fcdb09782d901d46ca95a7` |
| `initialize_membership_sources.py` | 2,625 | `72502b70c9a7e0854dd904c6aeb5a39f3dc2ac4288cedddad9bedc84a9488250` |
| `tests/test_c01_minisuite.py` | 15,484 | `2d7fafe8baae870e145a76cc819ed6119c1696911398de9f5fef494385ba4b77` |
| `README.md` | 7,125 | `2897e3aa7f0e9c8acd7380feb83551e2fd5fb38924c53aa114445104f259ea37` |

`THIRD-FIX-AUDIT.md`不自绑定，避免循环hash。

## 6. 请求复核什么、不请求什么

请求同一 reviewer重放：full-label read probe、actual read-set、nested bypass、feature_rows+self-hash、
outer seal mutation、zero/wrong bindings、旧640/640 oracle和metadata-only P3/P7。

即使这些局部通过，也只可能得到 scoped synthetic minisuite acceptance。仍未关闭：

- F4唯一机器语义；
- actual V2S D0/D1 receipts与fresh formal registry；
- actual sensitivity/CI、T role-null/zero-ingress；
- MODEL-INPUT完整matrix/deterministic math/双provider；
- 真实 Docker G、actual-shape rehearsal和formal 3200。

因此V3没有解锁MODEL-INPUT、G或3200，也没有把测试数或capability receipt外推为现实功效。
