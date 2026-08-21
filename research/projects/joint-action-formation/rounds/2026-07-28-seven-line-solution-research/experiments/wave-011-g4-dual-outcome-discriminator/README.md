# Wave 011 G4 dual-outcome discriminator

状态：`LOCAL_SYNTHETIC_DISCRIMINATOR_PILOT / NO FORMAL PROMOTION`

本目录只回答一个前置问题：能否先构造一个不会把“首次成功兑现”与“有界权威终态”混为
一谈、不会免费提供 current/Authority/fence/readback 结论、并能区分三种 interaction
quantifier 的小型可执行 evaluator。答案是：在当前 14-world 有限模型内可以；这还不是 G4
方案有效性或现实覆盖证据。

## Outcome 与时间谱系

每个 world 分开保存：

- `Y_success`：首次 attempt 是否成功，并满足 exact target 的预注册 postcondition；
- `Y_resolution`：是否得到可由指定 owner 重建、无未识别副作用的有界终态；
- `Y_effect`：目标权威域中的 intended Effect 是否实际发生；
- `Y_acceptance`：acceptance owner 是否实际接受。

Runner 强制执行：

```text
S0 → P0 → I(raw query / Authority / reservation / delegation)
   → S1 → P1 → first attempt → recovery/readback → four outcomes
```

P0 必须在任何 action 前冻结；P1 必须在 attempt 前冻结。形成动作和恢复后的成功不能回填
P0，正确拒绝可以 `Y_resolution=1` 且 `Y_success=0`。

## 14 个 world / 7 对

| pair | 类别 | 核心区别 |
|---|---|---|
| `P-SAME-SOURCE-ALIAS` | passive | registry/dashboard/model summary 同源于一个陈旧 cache |
| `A-STALE-HEAD-TWO-SEMANTICS` | active | `D0 != D1`，但 raw policy 分别是 pinned-allowed 与 current-required/revoked |
| `A-RESPONSE-LOST` | active | submit 均无响应，operation-keyed readback 分开已执行与无 Effect |
| `A-REVOCATION-AFTER-CHECK` | active | check 后撤销；revocable approval 与 binding-window commitment 分开 |
| `A-RESERVATION-NOT-CONSENT` | active | reservation 相同，owner 对 exact operation 分别批准或拒绝 |
| `H-DECLARED-UNQUERYABLE` | hard | 在冻结 pre-attempt action alphabet 内 raw transcript 相同，P0 success truth 相反 |
| `H-WRONG-OBJECT-READBACK` | hard | submit response lost，status API 始终返回同一错误对象，Effect truth 相反 |

`pair_auditor.py` 的量词不同：

- passive：只要求初始 public packet bytes 相同；
- active：必须存在至少一条合法 action trace 能分流或改变真值；
- hard：在声明的有限 action alphabet 上枚举空序列、所有单动作及全部两动作序列。

两个 hard pair 各枚举 `73` 条 plan，未发现不同 raw transcript。这个全称只在当前确定性模型、
动作集合和深度 `≤2` 内成立，不是开放世界的一般不可能性证明。

## Primitive 与真实状态转换

`primitive_services.py` 只返回 raw owner/provider record：

```text
read_revision
read_policy
get_token_state
read_dependency
request_authority
request_reservation
request_delegation
discover_status_api
submit_operation
read_operation_status
```

任何嵌套响应若出现 `head_current`、`fenced`、`authoritative`、`safe_to_rely`、
`ground_truth` 或 `expected_decision`，service 立即拒绝。Worker 必须自己验证 issuer、
operation/object binding、policy 语义、revision、scope、expiry 和 source contract。

提交时 target 实际校验：

- raw Authority/delegation revision；
- exact delegate 与 scope；
- reservation `fence_sequence`；
- exact operation/target；
- 当前撤销与 policy 状态。

response-lost world 实际执行 submit 与 operation-keyed readback；wrong-object readback 不计入
resolution。测试另行确认缺少 Authority revision 或 reservation sequence 时 target 零 Effect
拒绝，不接受 coordinator label。

## 四个 worker

| arm | 实现 |
|---|---|
| `STATIC_PACKET` | 不调用 primitive，只从初始 packet 预测 |
| `MATURE_COMPOSITE` | 按构件顺序验证 raw policy/IAM/Authority/reservation/readback |
| `SAME_PERMISSION_STRONG_CENTER` | 独立 issuer-indexed evidence ledger 与不同 query schedule |
| `LEGITIMATELY_DELEGATED_CENTER` | 通过同一 broker 向 owner 申请 exact-scope、限时 delegation |

四者只共享 transport client，不共享 decision function。成熟组合与强中心是不同 entrypoint、
不同源码和不同源码哈希。mutation test 把 mature binary 替换成 always-abstain 后，strong
center 的输出不变。所有 arm 获得同一世界的相同 primitive allowlist；合法委托不是隐藏
权限，它是任何方法都可选择、可拒绝且计费的 public action。

## 当前结果

P1 指标：

| arm | success TP/FP/TN/FN | success false reliance | success recall | success abstain | resolution TP/FP/TN/FN | queries / bytes / latency |
|---|---|---:|---:|---:|---|---|
| static | `5/5/0/0` | `0.500` | `0.625` | `0.286` | `0/0/0/0`，全 abstain | `0 / 0 / 0` |
| mature composite | `5/3/2/0` | `0.375` | `0.714` | `0.286` | `8/2/2/0` | `90 / 15352 / 386` |
| same-permission center | `5/3/2/0` | `0.375` | `0.714` | `0.286` | `8/2/0/0` | `90 / 15352 / 386` |
| delegated center | `1/0/5/2` | `0.000` | `0.143` | `0.429` | `8/2/0/0` | `70 / 11575 / 258` |

`false reliance` 是 conditional `FP/(TP+FP)`；abstention 不塞入 TN/FN。完整
`ABSTAIN_TRUE/ABSTAIN_FALSE`、P0/P1、pair class、actual four outcomes、披露、敏感度、
人工打断和 recovery 统计由 `runner.py --full` 输出，冻结摘要见
`results-summary.json`。

最重要的结果不是某个 winner：

1. static 的零查询以 `0.5` success false reliance 为代价；
2. mature 与 strong center 虽为独立实现，但在当前 success 分母得到相同结果；这只是有限
   等结果，不是函数 alias，也不是一般等价；
3. 两者仍有 `3` 个 success FP，说明 current/raw component acquisition 尚未闭合
   revocation/response-loss/hard ambiguity；
4. delegated center 在 binding delegation world 真实执行成功，但总体通过大量拒绝/弃权
   得到零 success FP，safe recall 只有 `1/7`；不能写成中心胜出；
5. mature 与 strong center 各有 `4` 次 ambiguous submit，执行了 readback，正确对象
   readback 为 `6` 个 world，重复 Effect 为 `0`；
6. resolution 的两个 FP 来自 wrong-object/readback hard boundary，证明 label 或 endpoint
   名称不能替代 exact-object owner record。

## 运行

```bash
cd /Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-011-g4-dual-outcome-discriminator

PYTHONPYCACHEPREFIX=/tmp/wave011-g4-pycache \
python3 pair_auditor.py

PYTHONPYCACHEPREFIX=/tmp/wave011-g4-pycache \
python3 runner.py --self-test

PYTHONPYCACHEPREFIX=/tmp/wave011-g4-pycache \
python3 runner.py --full

PYTHONPYCACHEPREFIX=/tmp/wave011-g4-pycache \
python3 -m unittest discover -s tests -v
```

研究者 B 的独立最小 broker 原型在 `prototype_b/`，从该目录运行其 6 项 tests。它不是
private-oracle scorer，也不进入上表分数；保留它是为了证明第二种 primitive/broker
实现路径和 response-loss reconciliation。

## 证据边界与扩量门

当前 fixture、oracle、主 runner 与 evaluator 仍由同一主研究会话整合；子研究者 A/C 分别
重建模型和攻击，但没有作为独立 truth owner 给主 oracle 盲评分。因此结果仍是本地合成
discriminator，不是独立 held-out。

不得扩到 2160/17280，直到至少：

- truth owner 冻结新的 blind world 且主实现者看不到 oracle；
- hard pair 的 action grammar/horizon 与目标主张重新预注册；
- target fence ignore/replay、Authority propagation delay 和并发 double-submit 进入独立
  adapter；
- P0/P1 的现实 exact operation、实际 owner 和 readback source 存在；
- 样本量按目标 UFR、实际 RELY exposure、cluster 单位与成本设计，而不是排列数量设计。
