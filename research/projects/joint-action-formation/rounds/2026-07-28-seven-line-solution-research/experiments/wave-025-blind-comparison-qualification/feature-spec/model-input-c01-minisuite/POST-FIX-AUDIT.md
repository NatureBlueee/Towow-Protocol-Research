# C01 minisuite V2 post-fix audit

> 日期：2026-08-01  
> 状态：`FIVE REDTEAM CASES REGRESSED / SAME REVIEWER RECHECK REQUIRED`  
> 边界：`NOT MODEL-INPUT CANON / ACTUAL D0 D1 UNKNOWN / G NOT RUN / 3200 NOT RUN`

## 1. 修复结论

本轮不保留 V1 总结作为目标，而是逐项响应 `INDEPENDENT-REDTEAM.md` 的五个内部 blocker。

| 红队发现 | V2 修复 | 回归证据 | 当前边界 |
|---|---|---|---|
| holdout labels 在 selection 前已驻留 | selection/prediction freeze 与 score 改为两个独立 Python 进程；freeze closed stdin 不接受 holdout labels，score 只收 frozen package、hash、holdout labels，不收 feature rows | 翻转全部 holdout labels 后 frozen document byte-exact 不变；向 freeze stdin 注入 `holdout_labels` 被拒；score payload 无 `categories/numerics` | 是当前工具的进程/接口边界，不是对恶意同 UID controller 的安全证明 |
| feature bytes 明文含 R/S 和 role-r/s | row ID 改为固定宽度 opaque hex；token/context 去除 class 明文；synthetic labels 独立落盘 | canonical feature bytes 禁词扫描；独立 calibration label inversion 保持 universe bytes 不变、改变规则/预测 | 不证明 actual runner membership provenance |
| F4 用 Boolean lookup 替换 conjunction | 删除 `00/01/10/11 -> class` 实现；F4 标记 `REJECTED_UNDERDETERMINED_NOT_EXECUTED`，candidate count 0 | P6 XOR 不再由 F4 假恢复；selected rule 为 null，固定失败码 | `FEATURE-SPEC.json` 仍需关闭 literal、orientation、fallback 与单 rule/规则集 |
| stable 只检查 holdout | stable 同时要求 calibration 与 holdout 的 R/S recall 全部精确为 1 | calibration 两个 label 对调、holdout 完美的反例现在 stable=false，失败码 `CALIBRATION_RECALL_NOT_EXACT_BOTH_CLASSES` | 仍是合成 recall，不是 class-wise CI |
| F1 OOV 与文档冲突 | 唯一选择：unknown token 被忽略；只按 frozen selector 的 presence/absence branch 预测；F1 OOV count 仅审计，不触发 row-level R fallback | P8 OOV-only 与 known+OOV 真值表；selector absent/present 分支逐项检查 | 这是 minisuite 候选语义，不代表已晋升 C01 canon |

来源边界也已修复：P2 改名为 conditional stable atom，状态为
`UNKNOWN_CONDITIONAL_CROSS_PHASE_STABILITY_NOT_EXPRESSED_BY_BOUND_PUBLIC_REGISTRATION`。结果不再声称
公开 D1 registration 已绑定 one-value-per-class/cross-phase-stable。private registry 未作为 evaluator
输入。actual D0 和 actual D1 均保持 `UNKNOWN / NOT_RUN`。

## 2. V2 合成结果

| case | 可执行结论 |
|---|---|
| P1 D0 stable exact atom | F1 calibration/holdout 双阶段双类 recall=1；仅为公开 D0 设计的机制类比 |
| P2 D1 conditional stable atom | 条件成立时 F1 双阶段恢复；前提未被当前公开绑定来源证明 |
| P3 per-slot fresh | F1/F2/F3 均不恢复；F4 未执行 |
| P4 context count-only | 仅 F2 恢复 |
| P5 numeric exact/missing | 仅 F3 恢复 |
| P6 XOR | F1/F2/F3 不恢复；F4 语义未闭合而拒绝，不再用 lookup 替代 |
| P7 context OOV | F2 calibration 完美、holdout 第二类 recall=0；未重选 |
| P8 F1 OOV selector absence | F1 双阶段恢复；20 个 OOV-only holdout rows 使用 absence branch |

V2 因此不作“四族都需要/不需要”的结论。当前只支持三个局部判断：

1. 公开 D0 设计的理想稳定 atom 与 F1 机制兼容，actual D0 仍 Unknown；
2. D1 只有在未来正式绑定跨 phase stable atom 前提后，才能把同样兼容性从 conditional 升级；
3. F2、F3 各自在 count 与 numeric/missing 合成攻击面产生 F1 没有的能力；F4 尚不能判断。

## 3. clean snapshot 复现

编辑期间，根级 runner 曾在“新实现 + 旧 artifacts/tests”的混合快照观察到 6 个 transient failure：
旧 `build_results` 签名、明文 fixtures、旧 F4 family 和旧 row-ID 断言。它们不是 V2 最终 receipt，也
没有被删除或包装成通过。完成同步重生后，从 clean current snapshot 独立执行：

```text
python3 feature-spec/model-input-c01-minisuite/c01_minisuite.py --check
=> byte-exact canonical check passed: 5 artifacts

PYTHONPYCACHEPREFIX=/tmp/wave025-c01-v2-pycache \
python3 -m pytest -q feature-spec/model-input-c01-minisuite/tests
=> 13 passed in 5.39s

PYTHONPYCACHEPREFIX=/tmp/wave025-feature-v2-pycache \
python3 -m pytest -q feature-spec/tests \
  feature-spec/collector-v1.1-candidate/tests \
  feature-spec/model-input-c01-minisuite/tests --disable-warnings
=> 163 passed in 48.88s

PYTHONPYCACHEPREFIX=/tmp/wave025-c01-v2-pycache \
python3 -m py_compile feature-spec/model-input-c01-minisuite/c01_minisuite.py \
  feature-spec/model-input-c01-minisuite/tests/test_c01_minisuite.py
=> exit 0
```

环境额外打印 urllib3/LibreSSL warning；它不改变测试结果，本轮没有据此作网络或 TLS 声明。

## 4. 最终字节

| 文件 | bytes | SHA-256 |
|---|---:|---|
| `C01-MINISUITE-CONTRACT.candidate.json` | 2,844 | `c23d974e0bcda29e4ee20b5dd2f57a03cae955bf3be5a9e76d14590ec5b5f88d` |
| `CASES-FEATURES.candidate.json` | 95,830 | `bcb23aad498b04fbf73e5c690424aaa257e1bc0bab800843639e80e248b1330e` |
| `CASES-LABELS.candidate.json` | 33,346 | `bcb8f708d326af8e4162625c3d45e097ccc1b3e01aef156387a2d86b41e7b3a9` |
| `FROZEN-SELECTIONS.candidate.json` | 320,962 | `b2f1031f34005fa6660aa332174db6c0f1ba47f12aa0ce87269c9be3ee955ba3` |
| `RESULTS.candidate.json` | 45,534 | `91df045cea253087434c2d4b92c2fb6bb16e839e30e4af9fe8ac061054a4aabd` |
| `c01_minisuite.py` | 42,157 | `01b298f699f5e971409911d9e975d5fae04d5bda6e87dc969161c009f3efe7cb` |
| `tests/test_c01_minisuite.py` | 12,755 | `7ad192720bf146ae640bba37b0039200fb526a423c907d04aa23d2b78ef39ce3` |
| `README.md` | 6,804 | `66eb199ff4bf0475cc40f7933a94d1467ae5c04d98aaecd379019de52752551e` |

`RESULTS` 绑定 contract、features、labels、frozen selections 四份输入 artifact，并绑定
generator、tests、README 当前 SHA。post-fix audit
本身不做自绑定，以避免循环 hash。

## 5. 仍未关闭

- F4 registered family 的唯一机器语义；
- actual V2S D0/D1 feature path、fresh formal registry 与 cross-phase receipt；
- actual control class-wise CI、T role-null、ablation 与零 ingress；
- model-input universe registry、matrix bytes、deterministic math、双 clean-room provider；
- 真实 Docker G、actual-shape cost rehearsal 与 formal 3200。

所以本审计只请求同一 reviewer 复查五个内部 blocker 是否关闭；它不请求晋升 MODEL-INPUT，不授权
G 或 3200，也不把 163 个测试通过解释为真实功效。
