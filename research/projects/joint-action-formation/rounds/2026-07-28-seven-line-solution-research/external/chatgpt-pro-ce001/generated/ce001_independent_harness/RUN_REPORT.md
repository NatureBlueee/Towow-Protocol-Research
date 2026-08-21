# CE-001 独立最小可执行模拟：运行报告

## 1. 定位

本包是**机制级参考模拟**，不是 Temporal、Camunda、PostgreSQL、OAuth、Cedar、OpenFGA、OPC UA 或任何真实产品的实测，也不声称覆盖 V2 的海量私有网络、开放发现、RelationEcology 或跨产品迁移。

它只检验一个较窄的问题：在 exact task、多个 Authority、不可把 ACK 当 Effect、Effect 后仍需 Acceptance/Settlement、资源撤销与协调器崩溃同时存在时，不同现有组织/工程路线能否得到正确终局。

## 2. 不共享决策根

四个 executor 分别拥有独立控制循环：

1. `direct_platform`：只使用 venue 自有资产；其他 case 返回 `NOT_APPLICABLE`。
2. `existing_authority_aware_portfolio`：确定性现有组合；分别查询 owner、形成已披露条件、搜索和确认资源、稳定 operation ID、target-side idempotency、exact readback、fencing、Acceptance、Settlement。
3. `bounded_human_institution`：电话、工单、人工审批、供应商目录和交接班；同一 Authority/action envelope，但时间与人工成本更高。
4. `naive_green_workflow`：静态路由、把 policy/admin 当 Authority、把回执或宽泛 success 当 Effect、崩溃后生成新 operation ID；作为弱反例。

共享部分仅为 raw owner/resource/target/settlement API、case simulator 与事后 evaluator。各 executor 不调用共同 `choose()`、候选选择器或 expected label。

附加独立性检查：

- 四个 executor 源码哈希不同；
- 只破坏现有组合的 exact readback，其他 executor 保持不变；
- 把 E5 的 owner truth 从拒绝移植为同意，检查 executor 是否真的读取 owner 决定；
- 移除 E2 的 condition-formation operator，检查结果是否因果改变。

## 3. 原生结果

默认 seed 7：

| Executor | Applicable | Correct resolution | Exact task success | Unsafe | Duplicate | Wrong-object | Total net value* |
|---|---:|---:|---:|---:|---:|---:|---:|
| direct platform | 1 | 1 | 1 | 0 | 0 | 0 | 864 |
| existing authority-aware portfolio | 8 | 8 | 7 | 0 | 0 | 0 | 5,540 |
| bounded human institution | 8 | 7 | 6 | 0 | 0 | 0 | 3,032 |
| naive green workflow | 8 | 0 | 4 | 2 | 1 | 1 | -26,382 |

`Exact task success=7` 对应七个可达 case；E5 的正确结果是无 Effect 的有界拒绝。

人工流程唯一的错误分辨发生在 E4：供应商 A 撤销后，人工扩大目录并找到 B，但此时已无法在 90 分钟内完成 45 分钟供电窗口，因此选择拒绝。它是安全的，但相对于仍可由更快组合完成的任务产生 liveness/value loss。

平台直达在 E0 的净值高于通用组合，说明正确的“最强现有解”应是路由组合，而不是所有 case 都强制进入同一协调流水线。

`naive_green_workflow` 有四次偶然产生 exact physical effect，但 0 次 correct resolution：它没有形成 O_Q/O_V Acceptance 与 Settlement；此外 E2/E5 越权，E3B 依赖错对象，E6 重复 Effect。

\* 净值仅为可替换的演示权重：成功且接受 +1000；正确拒绝保护价值 +250；unsafe -10000；duplicate -3000；wrong-object -2500；另扣资源、治理、时间与人工。它不是现实经济估值，正式实验必须预注册权重并做敏感性分析，同时保留原生向量。

## 4. 关键反事实

### E3B exact readback sabotage

- 正常现有组合：同一 operation ID 重试，产生 1 次 C7 Effect，正确完成；净值 752。
- 只把该组合的 exact readback 换成 broad success search：读取旧 C8 回执，C7 没有任何 Effect，却继续 Acceptance/Settlement；`wrong_object_reliance=true`，净值 -2718。
- 人工与弱基线的结果不因该代码破坏而变化。

这证明结果不是由一个共享 evaluator/selector 预定；exact-object readback 是承重机制。

### E2 formation ablation

- operator present：owner 首次返回 `UNKNOWN + missing conditions`；executor 只根据 owner 披露形成 purpose/noise 条件，owner 再决定后成功。
- operator removed：在完全相同 world 中停在 `DEFER`，无 Effect、Acceptance、Settlement。

这只支持“该有界、已披露条件形成步骤在本模拟内有因果作用”，不支持开放行动世界的一般 formation 主张。

### E5 truth transplant

- owner 拒绝时：现有组合与人工流程都 `REJECT`，且无 Effect。
- 把同一 case 的 owner truth 改为同意：两者都切换为 `SUCCESS`。
- 弱 workflow 在两种 world 都宣称 `SUCCESS`，所以它没有正确响应 Authority truth。

### E6 migration/replay

- 现有组合与人工流程：新 runtime 安装更高 target fence，旧 runtime replay 被 `stale_fence` 拒绝；只产生 1 次 Effect。
- 弱 workflow：崩溃后丢失 operation identity，以新 ID 重放；产生 2 次 Effect。

### Target fence persistence counterexample

- fence 持久：现有组合恢复成功，1 次 Effect，净值 758。
- 只改变一个目标侧条件——设备重启后丢失刚安装的 fence——旧 runtime replay 再次被接受；产生 2 次 Effect，`correct_resolution=false`，净值 -3242。

这说明 durable workflow、迁移 capsule 或新 coordinator 本身不能推出物理 exactly-once。目标侧持久 operation ledger/fence，或等价的物理 interlock，是该闭环的必要环境条件；缺失时应先补条件，而不是把失败自动解释为需要新的协调协议。

## 5. 50-seed 稳定性检查

运行 seeds 1–50，共 1,250 个 applicable executor-case runs：

- 现有组合：400/400 correct resolution；350/350 可达任务成功；0 unsafe、0 duplicate、0 wrong-object。
- 人工流程：350/400 correct resolution；300/350 可达任务成功；50 次均在 E4 因 deadline 不可达而安全失败。
- 平台直达：50/50 E0 correct。
- 弱 workflow：0/400 correct；100 unsafe、50 duplicate、50 wrong-object。

所有 arm/case 的离散结果签名在 50 个 seed 中稳定。由于随机化只改变非语义 vendor 顺序，这不是统计泛化证明，只是排除了对 fixture 顺序的依赖。

## 6. 运行

```bash
python3 run_harness.py --output results.json
```

主要文件：

- `run_harness.py`：模拟器、四个独立 executor、evaluator、sabotage/ablation/truth-transplant。
- `results.json`：默认运行的完整 actions、owner decisions、target ledger、Effect、Settlement 与评估。
- `batch-results.json`：50-seed 稳定性结果。
- `run-output.txt`：默认运行摘要。

## 7. 尚未解决

本模拟不能证明任何真实产品已闭合 CE-001，也没有覆盖：

- 真实电气设备、人员资质、法律 Authority 与传感器校准；
- 无 authoritative readback 时的不可区分边界；
- 亿级私有网络中的发现召回/披露/传播成本；
- 第三方噪声、安全外部性；
- 真正跨 Temporal/Camunda/自研引擎的语义迁移；
- target 重启后 fence/operation ledger 丢失；
- 长期 RelationEcology 的编译、复用与局部重开。

因此当前运行支持的结论是：**在模拟所给可查询 owner、持久 target ledger、exact readback、可安装 fence 与可形成短期条件的前提下，零新增协议的现有组合可以闭合这个 bounded episode。** 它不能据此外推关闭 V2 全局研究。
