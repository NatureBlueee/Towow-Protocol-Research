# 第二批 Codex CLI G1 最终返回

日期：2026-07-29  
状态：`MINIMAL RUNNABLE CANDIDATE COMPLETE / LOCAL SYNTHETIC / NO FORMAL PROMOTION`

## 结论

本 cohort 已交付并实际运行一个最小 G1 provenance discriminator。它完成了指定的边界修订：

- 冻结输入为 `IntentAtCoordinationInterface`，明确排除
  `vague goal/event → Intent`；
- 任何 positive interpretation 前先执行独立 `INVALIDITY_GATE`；
- 用多字段事件向量替代
  `INDEX_HIT / MODEL_HIT / ACTIVE_REVELATION` 等互斥单标签；
- \(t_0\) 回放只能使用当时合法 evidence path，不注入 \(t_1\) receipt、最终批准或
  operator 产物；
- 分开 public、t0 legal、final-proposal-only、full trace、operator removal 与 reversal；
- 分开 `L_benchmark` 与 `D_actual`，拒绝和合法 transcript 不可区分不算 actual-policy
  漏检；
- 分开 `C_RAW_UPPER`、`C_EQUAL_ACCESS` 与 `H_EQUAL_ENVELOPE`，并由 runner 而非 candidate
  自报重建成本；
- 自测 truth transplant、post-treatment evidence、wrong Authority、forbidden disclosure
  与 same-source alias。

本轮没有证明 NAC、通爻或新机制独特，也没有发现必须发明新协议的 residual。强中心、成熟
组合、人类或更小程序完整通过都是正结果。

同时得到一个不能掩盖的负结果：

> 当前两个可运行实现都只做到模块/接口纪律隔离；worker 与 oracle 仍处于同一 Python/文件
> 权限域，不能声称对反射或恶意 worker 无泄漏。

因此本轮产物是可执行的 discriminator candidate，不是可用于正式方法胜负或状态晋升的
leak-free evaluator。

## 实际多 Agent

本 CLI 实际创建了三名内部研究者，均有独立 agent identity、独立返回和落盘产物；不存在
capability failure：

1. `/root/g1_a_evaluator`
   - 职责：从原问题、V1/V2 和 G1 边界独立重建 evaluator；
   - 产物：`experiments/wave-011-g1-provenance-discriminator/A-EVALUATOR.md`；
   - 结果：冻结 invalidity gate、事件向量、六类回放、双分母、公平 arms、10-world
     population 与 24 条 release assertions；
   - 独立性：未读取 B/C 产物。
2. `/root/g1_b_discriminator`
   - 职责：独立设计并实现最小可运行 discriminator；
   - 产物：`experiments/wave-011-g1-provenance-discriminator/b_candidate/`；
   - 结果：12 worlds、5 个 workers、runner、oracle、operator removal/reversal 与 18 项
     tests；
   - 独立诊断：`MATURE_COMPOSITION` 的 `D_actual` recall 为 `5/6`，但有 3 个 invalid
     worlds，hard gate 失败；明确报告 hostile same-process isolation 不成立。
3. `/root/g1_c_attack`
   - 职责：不知道预期胜者，专门攻击 oracle、标签、分母、公平性和
     Authority/disclosure 泄漏；
   - 产物：`experiments/wave-011-g1-provenance-discriminator/C-ATTACK.md`；
   - 结果：M01–M17 mutation spec、10-world 骨架、G0–G8 invalidity gate 与 release gate；
   - 独立性：撰写时未读取 A/B 产物。

主会话没有把 Agent 数量当作独立证据；它读取并比较三份返回，另行实现、修复和复测 canonical
候选。

## 文件

主目录：

`research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/`
`experiments/wave-011-g1-provenance-discriminator/`

关键文件：

- `README.md`：范围、运行方法、结果和未解决边界；
- `fixtures/method_visible_worlds.json`：10 个 opaque-ID method-visible worlds；
- `oracle/private_oracle.json`：独立 structural truth、policy、Authority、时间和来源根；
- `provenance_discriminator/model.py`：冻结对象与 fixture/oracle loaders；
- `provenance_discriminator/workers.py`：public、equal-access center、human、raw upper、
  final-only 与 trace replay；
- `provenance_discriminator/evaluator.py`：positive 前 hard gate、事件向量、双分母与
  runner-controlled cost；
- `provenance_discriminator/runner.py`：8 个 arms/interventions、population receipt 与
  worker implementation hash；
- `tests/test_discriminator.py`：主候选 19 项 tests；
- `A-EVALUATOR.md`、`C-ATTACK.md`：独立研究与攻击返回；
- `b_candidate/`：B 的独立 12-world 实现与 18 项 tests。

本轮没有修改 `research/NOW.md`、`PROGRAM.md`、LineContract、Problem、MechanismProfile
或任何正式状态。

## 主候选结果

主 population 为 10 worlds：

```text
|L_benchmark| = 9
|D_actual| = 2
```

| arm | actual-policy recall | structural recall | hard gate |
|---|---:|---:|---|
| public baseline | `1/2` | `1/9` | `FAIL`：wrong Authority、same-source alias |
| equal-access center | `2/2` | `2/9` | `FAIL`：wrong Authority、same-source alias |
| human equal-envelope | `2/2` | `2/9` | `FAIL`：wrong Authority、same-source alias |
| raw upper | `2/2` | `2/9` | `PASS`，但只是合法 raw 上界且只在相应 worlds 可运行 |
| full trace | `2/2` | `4/9` | `FAIL`：wrong Authority、forbidden disclosure、alias |

解释：

- public baseline 漏掉唯一非 public、但 \(t_0\) 有合法 owner path 的 `D_actual` world；
- equal-access center 与 human 在当前很小的 `D_actual` 分母上均为 `2/2`，但遇到错误
  Authority 和同源 alias 时会提交 invalid candidate，所以不能称为 solution；
- full trace 多出的两个 structural positives 来自 operator-created capability/terms
  qualification；remove 后不成立，reverse 后因 revoked/non-qualifying evidence 被拒绝；
- zero-disclosure exists/absent pair 的合法输出相同；exists world 留在 structural
  boundary，不进入 actual-policy miss；
- raw upper 是信息上界，不是 equal-access 胜者。它的 raw exposure 高于 equal-access，
  且 raw centralization 不合法的 worlds 正确停止。

主 runner 固定并报告：

```text
method_visible_sha256 =
4a6974b9b86c16f6a4fc4f858324345279b0d4fe0abe7b9799be478eb23d717a

private_oracle_sha256 =
2efd2dc4eb714d9c726b97d1d252669e3720c44b11c6e8973817e8c09923c6e7
```

这些 hash 是本次本地 population receipt，不是不受同权限进程篡改的外部锚。

## 验证

主候选：

```text
python3 -m unittest discover -s tests -v
Ran 19 tests
OK
```

B 独立候选：

```text
python3 -m unittest discover -s b_candidate/tests -v
Ran 18 tests
OK
```

附加检查：

- `python3 -m compileall -q provenance_discriminator tests b_candidate`：通过，pycache 写入
  `/tmp`；
- 两份 JSON fixture/oracle 由 `python3 -m json.tool` 解析：通过；
- `git diff --check`：通过。

已实际拒绝或保持边界的攻击包括：

- truth transplant；
- \(t_1\) receipt 注入 \(t_0\)；
- valid key / wrong Authority；
- true fact / forbidden disclosure；
- same-source aliases 冒充独立证据；
- candidate 自报 positive label、cost、arm 或 intervention；
- target、\(Q\)、必要主体或 G1 lifecycle status 偷换；
- operator removal/reversal；
- refusal/indistinguishability 分母污染；
- raw upper 与 equal-access 混用；
- human action envelope 与人工成本遗漏。

测试通过只证明这些有限 synthetic invariants 和已实现 attacks 被当前代码捕获，不证明现实
频率、真人理解、跨域 Authority、产品可靠性、部署或 V1/V2 一般解。

## 未解决边界与下一步

当前主候选的真实隔离声明是：

```text
MODULE_AND_INPUT_DISCIPLINE_ONLY_NOT_HOSTILE_SAME_PROCESS
```

不能支持：

```text
LEAK_FREE_EVALUATION_AGAINST_REFLECTIVE_OR_MALICIOUS_WORKER
```

原因不是测试数量不足，而是权限域没有分开：worker 理论上仍可反射模块、遍历文件或攻击
session 私有字段。下一条最有价值行动是把 worker 移到独立进程/容器或只读权限域，只传
method-visible bytes 与受控 action RPC；oracle、keys、population receipt、trusted
intervention 和 meter 由 worker 无权读取/改写的 controller 持有。然后把 C 的 M01–M17
逐项变成跨权限域 mutation tests。

在此之前，不应：

- 根据本轮 `2/2` 或 `5/6` 选择方法胜者；
- 把 full-trace 的 operator positives 倒灌为 \(t_0\) discovery；
- 把本轮绿灯晋升为正式 evaluator、机制状态或通爻/NAC 证据；
- 扩成 30+ episodes 来掩盖 isolation residual。

本轮没有联网、没有调用外部 Pro/AgentKey，也没有发送 NAC 专利材料或其他非公开内容。
