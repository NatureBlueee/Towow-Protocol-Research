# Wave 024 Authority-epoch S/R/U twin

状态：`MIXED SCOPED RESULT / INDEPENDENT EVALUATOR PASSED`

这是 `QUESTION.md` 的最小可运行本地 twin。它使用同一冻结 candidate 和 exact CE-001 数字任务，
运行三个世界：

| 世界 | Target execute 前的事实 | 预期原生结果 | 评分 |
|---|---|---|---|
| S | Target 尚未消费 superseding fence | Effect 1；Acceptance 2；finality 1；retry 0 | 参与 S/R discriminator |
| R | Target 已 durable 安装 matching revoked fence 并 ACK | stale refusal 1；Effect/Acceptance/finality/retry 均 0 | 参与 S/R discriminator |
| U | Authority 已有 revoke record，但 Target 未 ACK/未安装 | Target 按其本地 current view 决定 | `CONCURRENT_OR_UNORDERED/NOT_SCORED` |

## 运行

```bash
cd /Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-024-authority-epoch-twin
python3 run.py --output-root /tmp/wave024-runs
```

一次运行约三秒，输出新的 `twin-<uuid>/`。每个 world 都保留 Target、ACK proxy、candidate source
state、三个 owner store 的 SQLite 原生文件与 JSON receipt；root 还保留 Authority 和 lab registry
store。`TWIN-ARTIFACT.json` 的状态有意保持
`RUN_COMPLETED_PENDING_INDEPENDENT_EVALUATION`，runtime 不给自己签发接受结论。

## 回归与独立 evaluator

```bash
PYTHONPYCACHEPREFIX=/tmp/wave024-pycache python3 -m pytest -q -p no:cacheprovider \
  tests/test_runtime.py tests/test_independent_evaluator.py
python3 independent_evaluator.py \
  artifacts/twin-91591fa0c44344839e6c3a23b5dca258
```

当前 34 个测试通过：24 个 runtime/语义回归覆盖完整 S/R/U、S exact idempotence、R
fence-before-ingress、ACK 丢失恢复、owner 固定信任，以及 wrong Q/object/Target/operation、
非 revoke successor、expired delegation，并验证 Authority 只接受由启动时固定 lab root 认证、
Target 签名且 exact scope 完整匹配的 S predecessor receipt；10 个 evaluator 测试不导入 runtime，
直接重算 SQLite、签名、hash 与 root→world binding，并验证一致重写不能制造假接受。

旧运行 `twin-6184157568564a38831c4b7c4ad737f5` 虽让 Authority 签入 predecessor hash，
Authority 却没有自行验证 controller 传入的完整 Target receipt，现只保留为被反例重开的历史，
不再进入当前证据闭包。

## 文件

- `QUESTION.md`：冻结原问题、claims 与 S/R/U 判据；
- `DESIGN.md`：运行域、原子事务、恢复、复用/新增边界；
- `twin_runtime.py`：唯一 candidate/runtime artifact；
- `run.py`：最小运行入口；
- `independent_evaluator.py`：不导入 runtime 的原生证据重算器；
- `tests/test_runtime.py`、`tests/test_independent_evaluator.py`：runtime 与 evaluator 回归；
- `RED-TEAM-PREFLIGHT.md`、`ATOMICITY-MODEL.md`、`PRIOR-ART.md`、`TRANSFER-MATRIX.md`：独立
  前置审查材料，不是 runtime 自证。

## 结论边界

独立结果为 mixed：`TARGET-CONSUMED-FENCE`、`EXACTLY-ONCE-RECOVERY`、
`NATIVE-POSTCONDITIONS` 为 `SUPPORT_SCOPED`；完整 `ISOMORPHIC-BLINDNESS=FAIL`；
`GLOBAL-AUTHORITY-CURRENTNESS=NOT_TESTED`。U 的 Target 会按尚未更新的本地 current view 提交，
但严格 `NOT_SCORED`，不能被用作全局 currentness 证据。

本 runtime 仍不声称 Target crash persistence、hostile same-user blindness、外部不可改写 root、
现实法律 Authority、物理 Effect、生产有效性或 A1–A5 胜者。详见 `DESIGN.md`。
