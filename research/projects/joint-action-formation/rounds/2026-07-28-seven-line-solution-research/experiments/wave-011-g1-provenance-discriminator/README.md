# Wave 011 G1 provenance discriminator

状态：`LOCAL SYNTHETIC INSTRUMENT CANDIDATE / NO FORMAL STATUS CHANGE`

这个目录交付一个小型、可执行的 G1 provenance discriminator。它不比较“谁更像通爻”，
而是检查一个候选究竟来自 public information、\(t_0\) 合法 evidence path，还是实际
operator 在 \(t_1\) 产生的新资格、条款或能力；任何正解释前先通过独立
`INVALIDITY_GATE`。

## 冻结边界

- 输入从 `IntentAtCoordinationInterface` 开始。
- `vague goal/event → Intent` 明确排除，不进入 G1 分母。
- G1 最多输出 `CANDIDATE_NOT_COMMITMENT`，不推出 Capability、Mandate、Commitment、
  Effect、Acceptance 或 Settlement。
- `L_benchmark` 是冻结 structural population；`D_actual` 只含在 \(t_0\) policy、action
  envelope、budget 与 horizon 内存在合法 evidence path 的机会。
- signed refusal、policy-unfindable 与合法 transcript 不可区分的存在 world 不算
  actual-policy 漏检。

## 目录

- `fixtures/method_visible_worlds.json`：10 个 opaque-ID method-visible worlds。
- `oracle/private_oracle.json`：独立 structural truth、Authority、policy、时间和来源根。
- `provenance_discriminator/`：workers、invalidity gate、事件向量、runner 与成本重建。
- `tests/test_discriminator.py`：主候选的攻击与边界测试。
- `A-EVALUATOR.md`：内部研究者 A 独立重建的 evaluator contract。
- `C-ATTACK.md`：内部研究者 C 在不知道预期胜者时形成的 M01–M17 攻击规范。
- `b_candidate/`：内部研究者 B 独立实现的 12-world 候选与测试；保留作竞争实现，不作为
  主实现的“第二份证据”合并计数。

## 主候选

### 回放

runner 分开执行：

1. `PUBLIC_BASELINE`
2. `T0_LEGAL_EVIDENCE_PATH`
3. `FINAL_PROPOSAL_ONLY`
4. `FULL_ACTUAL_TRACE`
5. `REMOVE_OPERATOR`
6. `REVERSE_OPERATOR`

`FINAL_PROPOSAL_ONLY` 只保留 \(t_0\) 当时合法 evidence；最终 proposal 中引用的 \(t_1\)
receipt 不会被注入。operator removal/reversal 与 full trace 的差异进入事件向量，而不是
被压成 `INDEX_HIT / MODEL_HIT / ACTIVE_REVELATION` 中的一个标签。

### 基线

- `PUBLIC_BASELINE`：只读公共索引。
- `C_EQUAL_ACCESS`：只使用共同 action envelope 内的 \(t_0\) 合法路径。
- `H_EQUAL_ENVELOPE`：与中心使用相同动作集合，另计 human minutes 与等待。
- `C_RAW_UPPER`：合法 raw-information 技术上界，单独计完整 exposure，不参加
  equal-access 算法归因。

worker 的实现 hash 会进入报告；成本、trusted arm 与 intervention 由 runner 冻结，candidate
自报的 label、cost、safety 或 source arm 不参与 gate 和计费。

### 当前诊断结果

冻结主 population 为 `|L_benchmark|=9`、`|D_actual|=2`：

| arm | actual-policy recall | structural recall | hard gate |
|---|---:|---:|---|
| public baseline | `1/2` | `1/9` | `FAIL`：wrong Authority、same-source alias |
| equal-access center | `2/2` | `2/9` | `FAIL`：wrong Authority、same-source alias |
| human equal-envelope | `2/2` | `2/9` | `FAIL`：wrong Authority、same-source alias |
| raw upper | `2/2` | `2/9` | `PASS`，但只是合法 raw 上界且只在相应 worlds 可运行 |
| full trace | `2/2` | `4/9` | `FAIL`：wrong Authority、forbidden disclosure、alias |

所以 `2/2` 不能称为 scoped solution：recall 不会抵消 Authority、disclosure 或 source
independence 的硬失败。full trace 相对 \(t_0\) 多出的两个 valid structural paths 被事件
向量归为 operator-created qualification；removal 会使其不成立，reversal 会因 revoked /
non-qualifying evidence 被拒绝。

B 的竞争实现给出 12-world 诊断：`MATURE_COMPOSITION` 为 `5/6 D_actual`，同时有 3 个
invalid worlds，因此同样不能称为 solution。强中心、成熟组合、人类或更小程序若在后续
隔离运行中完整通过，都是正结果。

## 运行

在本目录执行：

```bash
python3 -m unittest discover -s tests -v
python3 -m provenance_discriminator.runner

python3 -m unittest discover -s b_candidate/tests -v
python3 -m b_candidate.runner
```

本轮主候选 `19/19`，B 候选 `18/18`。这些绿灯只证明已实现的 fixture/invariant 与攻击
按预期工作，不证明现实频率、真实主体理解、跨域 Authority、部署或 V1/V2 一般解。

## 已覆盖的指定攻击

- truth transplant；
- post-treatment evidence 注入；
- valid key / wrong claim Authority；
- true fact / forbidden disclosure；
- same-source evidence alias；
- candidate 自报 label、cost、arm/intervention；
- operator removal/reversal；
- refusal/indistinguishable 分母污染；
- `C_RAW_UPPER` 与 `C_EQUAL_ACCESS` 混用；
- human off-envelope 成本遗漏的结构性检查。

## 尚未关闭的边界

主候选把 method-visible fixture 与 private oracle 分文件，workers 不导入 oracle，case ID
也不暴露语义标签；B 候选通过 session API 隔离二者。但它们仍运行在同一个本地 Python
权限域。一个反射或恶意 worker 可以尝试读取模块全局、文件系统或 session 私有字段。

因此本候选明确不能支持：

```text
LEAK_FREE_EVALUATION_AGAINST_REFLECTIVE_OR_MALICIOUS_WORKER
```

下一步若要把它升级为可用于方法胜负的 evaluator，必须把 worker 移到独立进程/容器或只读
权限域，只传 method-visible bytes 与受控 action RPC；oracle、keys、population receipt、
trusted intervention 与计量日志由 worker 无权读取或改写的 controller 持有。随后重新运行
C 的 mutation suite，而不能用本轮同进程绿灯晋升正式状态。
