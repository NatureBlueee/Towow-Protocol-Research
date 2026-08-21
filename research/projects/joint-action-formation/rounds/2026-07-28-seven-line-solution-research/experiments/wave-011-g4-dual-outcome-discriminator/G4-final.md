# 第二批 Codex CLI G4 cohort 最终报告

日期：2026-07-29  
状态：`LOCAL_SYNTHETIC_DISCRIMINATOR_PILOT_COMPLETE / NO FORMAL PROMOTION`

## 总判断

本 cohort 已把 Wave 010 的单一 `safe_to_rely` 标签拆成两个不可替代的预测目标和四个实际
结果，并做成 14-world 可执行 pilot：

```text
P0 prospective prediction
→ I actual raw query / Authority / reservation / delegation
→ P1 newly frozen prediction
→ first attempt
→ Y_success / Y_resolution / Y_effect / Y_acceptance
```

Evaluator 与 interaction quantifier 在当前有限模型内有分辨力：

- passive、active、hard 三类 pair 分开；
- 4 个 active pair 都有实际 lawful distinguishing trace；
- 2 个 hard pair 各审计 73 条深度 ≤2 action sequence，raw transcript 全等且初始
  `Y_success` 相反；
- always-rely 与 all-abstain mutation 得到不同 false-reliance/recall/abstention；
- mature worker 被 sabotage 后 strong-center worker 不变，排除了 Wave 010 的函数 alias；
- response lost、readback、wrong object、Authority revision 与 reservation sequence 均执行
  实际状态转换，不是 recovery label match。

这只证明 harness 已经值得进入下一轮 blind holdout；不证明任何 arm 已解决 G4。

## 实际内部子 Agent

本 CLI 实际并行创建并收到三名内部研究者返回，没有模拟：

1. `/root/g4_outcome_reconstruction`（A）：写入
   `notes/researcher-a-outcome-model.md`；独立重建四 outcome、P0/I/P1 与 18-world/9-pair
   候选。主实现采用其双结果与时间谱系，将分母压缩为 14 个因果不同 world。
2. `/root/g4_paired_runner`（B）：写入 `prototype_b/`；独立实现 6-world raw primitive、
   JSONL broker、mature worker、实际 response-loss readback/reconciliation，`6/6` tests
   通过。该原型不含 private oracle，不进入主分数。
3. `/root/g4_adversarial_attack`（C）：写入 `notes/researcher-c-attack-plan.md`；给出 free
   current/Authority/fence/readback、method alias、center fairness、legitimate delegation、
   same-source alias、label recovery 与 scale illusion 的 13 项通过门。

最终 oracle、evaluator、同权限 strong center 和跨返回综合仍由主研究者负责，没有把正式
研究判断外包。

## 交付

- `fixture.json`：14 worlds / 7 pairs 公共候选；
- `private_oracle.json`：隐藏 service state 与 truth configuration；
- `primitive_services.py`：raw owner/provider service 与实际 target checks；
- `worker_runtime.py`：只含 JSONL transport；
- `workers/`：static、mature composite、same-permission strong center、legitimately
  delegated center 四个独立进程；
- `runner.py`：P0/P1 phase gate、broker、actual attempt/recovery、oracle-preserving run；
- `evaluator.py`：success/resolution confusion、false reliance、safe recall、abstention、
  four outcomes 与成本；
- `pair_auditor.py`：三种 interaction quantifier；
- `tests/`：主实现 mutations 与 integration tests；
- `prototype_b/`：研究者 B 的第二种独立 runner 原型；
- `results-summary.json` 与 `README.md`。

## 精确结果

主 14-world P1：

| arm | success TP/FP/TN/FN | success UFR conditional | success recall | abstention | resolution TP/FP/TN/FN |
|---|---|---:|---:|---:|---|
| static | `5/5/0/0` | `0.500` | `0.625` | `0.286` | 全 abstain |
| mature composite | `5/3/2/0` | `0.375` | `0.714` | `0.286` | `8/2/2/0` |
| same-permission center | `5/3/2/0` | `0.375` | `0.714` | `0.286` | `8/2/0/0` |
| delegated center | `1/0/5/2` | `0.000` | `0.143` | `0.429` | `8/2/0/0` |

成本总量：

| arm | query | disclosed bytes | latency ticks | sensitivity | human interruptions |
|---|---:|---:|---:|---:|---:|
| static | 0 | 0 | 0 | 0 | 0 |
| mature composite | 90 | 15352 | 386 | 252 | 12 |
| same-permission center | 90 | 15352 | 386 | 252 | 12 |
| delegated center | 70 | 11575 | 258 | 166 | 6 |

这些 latency/disclosure 是 fixture 成本账，不是现实测量。成熟组合与同权限中心相同 success
结果来自不同源码和不同 evidence organization；它是“当前分母内结果相同”，不是因果等价。
合法委托中心只在取得 exact-scope binding delegation 后成功，拒绝或非 binding receipt 不会
获得 Authority；零 FP 是低 recall 的选择性结果，不是总体优越。

实际 recovery/readback：

- mature 与 strong center 各有 4 次 ambiguous submit response；
- 两者各观察到 6 个 correct-object readback；
- 所有 arm duplicate Effect world 为 0；
- wrong-object record 在成功/无 Effect 两侧都不计 resolution；
- `Y_effect=1, Y_acceptance=0` 的机器 world 实际存在，验证二者未被合并。

## 实际测试

通过：

```text
主实现 unittest: 13/13 PASS
研究者 B 原型 unittest: 6/6 PASS
pair audit: 7/7 pairs PASS
runner --self-test: PASS
py_compile: PASS with PYTHONPYCACHEPREFIX=/tmp/wave011-g4-pycache
```

初次不带 `PYTHONPYCACHEPREFIX` 的 `py_compile` 因 macOS 默认
`~/Library/Caches/com.apple.python/...` 在当前 sandbox 不可写而失败；这不是代码失败。随后
按仓库既有方式把 bytecode cache 指向 `/tmp`，编译通过。没有通过扩大权限绕过。

## 当前新判断

1. success 与 resolution 的分离是实质性的：正确拒绝/无 Effect 可 resolution 成功而
   success 失败；wrong-object endpoint 可看似有 status 却 resolution 失败。
2. current evidence 的价值来自实际 raw query 与 binding，不来自字段名。stale-head 两语义
   必须读 policy/revocation，`D0 != HEAD` 本身没有方向。
3. reservation 只有在 worker 携带 raw sequence 且 target 实际校验时才形成 fence；本地
   ledger 的 `RESERVED` 标签不够。
4. 同权限中心可以与成熟组合得到相同正结果；合法委托中心也是正向候选。拓扑本身既不是
   成功证据也不是作弊证据。
5. hard boundary 只在完整冻结的 lawful action/horizon 下成立。初始 packet 相同的四个
   active pair 都被合法 action 分流，不能用来宣称不可能。
6. 当前三种 active policy 仍有 success/resolution FP。成熟组件“存在”没有自动闭合本次
   exact operation。

## 残余与停止边界

当前不扩到 2160/17280。真实残余是：

- 主 oracle/evaluator 与主实现仍来自同一 cohort，不是 blind independent truth owner；
- hard interaction universal 只覆盖有限 action alphabet 与深度 2；
- 未独立注入 target 忽略/replay fence、Authority propagation delay、并发 double-submit；
- 没有真实 X1 finalized output、现实 Principal、生产 Effect 或真人 Acceptance；
- 当前分母不能决定 derived Capability Claim 是否有不可由更小 primitive 重建的增益；
- synthetic 成本不能换算成现实事故率、控制面负载或商业净值。

下一项高价值行动是让独立 truth owner 冻结新的 exact-operation holdout 和 adapter，再让当前
四个 worker 在未知 oracle 上运行。只有 blind holdout 重复暴露同一 residual，才讨论扩量或
新 primitive；本 cohort 不修改 NOW、PROGRAM、LineContract、MechanismProfile 或正式状态。
