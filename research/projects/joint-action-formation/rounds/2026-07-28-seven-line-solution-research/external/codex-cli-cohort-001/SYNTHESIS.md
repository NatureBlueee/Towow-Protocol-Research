# Codex CLI cohort 001：claim-level 综合

日期：2026-07-29  
状态：`READ_ONLY / NO FORMAL PROMOTION / NO COVERAGE CLAIM`

## 证据边界

本 cohort 有七个独立启动的 CLI 母线 session（G1–G7）；每个母线又分别启动 A/B/C
子研究者，承担问题重建、建设性求解与反例攻击。该编排产生竞争性解释，但共享仓库历史、
任务材料和相近模型环境，不构成七次或二十一次独立证据。

G1/G2/G3/G6 的 final 直接保存在本目录。任务交接记录 G4/G5/G7 原 CLI session 已结束，
但当时缺少持久化 raw final；当前
[`G4-final.md`](./G4-final.md)、[`G5-final.md`](./G5-final.md)、
[`G7-final.md`](./G7-final.md) 只作为恢复出的 terminal conclusion 使用，不当作 raw
transcript、receipt、哈希链或额外独立验证。缺失内容保持缺失，不补造。

## 改变当前问题的结论

当前没有证据表明 G1–G7 各自缺一个新机制。更承重的问题是：

> 成熟 center、planner、workflow、policy、reservation、event、readback 与人工制度，
> 能否在 fresh task 上产生并无损传递 current、owner-scoped、
> object/version/causal-bound evidence；actual policy 能否仅凭合法 observation 到达；
> target truth 与 dependency 能否在漂移、恢复和迁移后继续由原 owner 重建？

因此，normalized input 下成功而 raw end-to-end 失败，指向 observation/semantic formation；
跨 connector 丢 owner/head/version/负状态/causal identity，指向 conformance；合法 transcript
本就不可区分时，正确动作是创造 observation 或保持 `Unknown`，不是发明新协议。

## 会改变实验或实现的 claim

| 线 | 可保留结论 | 必须撤回或保持 Unknown |
|---|---|---|
| G1 | Wave002 的 `0/8、1/8、5/8` 支持目录与端侧投影互补；Wave009 在固定 grammar 和预置 provider 菜单中 `10/10` | 没有测广义 query genesis、开放维度发现或真实 privacy safety；必须拆开 discovery 与 handoff |
| G2 | 强中心 B0 与成熟组合 B5 在可信 parent、显式语义、单进程原子 reservation 的 24 个本地 world 中均闭合 G2/G5/integration | 完整 T2/T3/T4 residual 未测；authority JSON、policy Allow、workflow green 或 aggregate signature 不能代替 owner 的 current attempt permit |
| G3 | 成熟 planning/case/HITL 组合覆盖 QHM-1 的有限可解 worlds，candidate 无独有成功 | 未检验 QHM-2 actual policy；现有 contract 不能区分 `ACTUAL_POLICY_MISS / BOUNDED_UNREACHABLE / AUTHORIZED_NEW_EPISODE / INVALID_SUBSTITUTION` |
| G4 | exact-operation reliance decision table 与不可观察性反例可保留 | 12-world 是 `ALIAS_BY_CONSTRUCTION`：strong center 直接调用 mature composition，fixture 给出答案字段，recovery 未实际执行；不是方法比较 |
| G5 | 当前最佳方案是成熟 stack 加薄的 owner-bound conformance adapter；局部模型中没有稳定新 residual | 局部 G2/G5 residual 为零不能外推到真人 Relation、分布式原子性、自然语言或生产 Authority |
| G6 | 在即时、正确、免费的 owner truth 下，成熟组合和强中心都能把答案路由到预期输出 | `7/7` 是 perfect-oracle wiring；没有验证 operation、因果归属、object/version、head、freshness、并发、签名或 false negative |
| G7 | owner dependency query、current-head closure 与人工 amendment 的职责边界已形成候选设计 | T6 `UNKNOWN_NOT_RUN`；没有两类已完成 base trace，也没有 low-cost scoped reopen 的净价值证据 |

Wave007 的 A2/B2/C2 只支持 attempt-time idempotency、current-head binding、L3/L4 与
one-shot/bounded reuse 的局部回归，不是 blind holdout、独立实现或现实恢复证据。

由 G4/G6 共同暴露出的关键错误是：同一 `world.truth`、决策函数、expected table 或 keyspace
同时喂给方法与 evaluator，会把“正确接线”误报为“闭合未知”。

## 实现必须据此修改

1. 分开 `D_discovery(t)` 与 `H_handoff(t)`；发现后、handoff 前撤销应记“发现成功、阻断正确”。
2. exact-operation reliance 冻结 operation、executor、environment、artifact/version、
   distribution、permission、resource、recovery、horizon；`RELY` 仍须过 execution-time
   Authority gate。
3. 分开 exact RelationVersion stance、proposal/award acceptance、output Acceptance、
   authorized new episode 与 settlement closure。
4. 用 task-specific typed DAG 取代固定五层 ladder；每个状态绑定 `object_kind`、exact
   version、owner/head 与 causal edge。
5. 既有 amendment/sign workflow 可以首次产生 operative token；这叫 condition creation，
   不自动证明需要新 planner primitive。
6. 一个正式事实只保留原 owner。center、adapter、policy、workflow、hash、signature 与
   event bus 只能查询、验证、传输或派生，不能建立第二套正式 truth。
7. migration 必须保留 `UNKNOWN/REFUSED/STALE/REVOKED/CONFLICT`、opposition、exit、
   compensation residual 与旧 Acceptance，不能压成 false、success 或 generic failure。

## 下一轮最小有效实验

1. **先修 evaluator。** 加入 G3 四类结果；receipt 保存合法 observation、inventory
   completeness、counterfactual 与 task diff；G1 从 disclosure log 重建 privacy；
   G4/G6 逐层评分 false promotion、false negative、wrong owner、wrong object/version。
2. **移除 alias 与免费 oracle。** arms 独立实现；owner state、Authority、dependency、
   migration 使用不同 service/package、runtime key 与 append-only ledger；API 只返回
   owner-signed raw receipt 及 `CURRENT/REVOKED/UNKNOWN/REFUSED/STALE/LOST/CONFLICT/TIMEOUT`。
   prediction 先冻结，再注入 drift；recovery 必须真的取得新 head/authorization、迁移并
   readback。
3. **建立有效分母。** T3 候选在独立冻结 S0/owner/action/poststate/oracle 前不入分母；
   T2/T4 使用 fresh hidden cases；G4/X2 只能接 actual finalized X1 outputs；G7 至少要有
   两个异质任务族的 completed synthetic base trace。
4. **同臂双轨比较。** `REPRESENTATION-NORMALIZED` 测纯求解/conformance；
   `END-TO-END` 从原始材料计入 elicitation、HITL、披露、等待、治理、恢复和迁移。共同 arms
   是 lawful strong center、mature composition、human institution；candidate 只在稳定
   residual 出现后加入。

只有同一断点在两个异质任务族、fresh holdout 与迁移后稳定复现，并让强中心、成熟组合和
人工制度在同一 `BE0` 下共同失败，才登记新有界机制候选。若成熟 adapter 与 owner API
闭合断点，residual 为零，应直接采用。

## 当前最窄状态

```text
MATURE_COMPONENT_KERNELS = POSITIVE_SCOPED
G1_GENERAL_DISCOVERY = NOT_MEASURED
G2_G5_LOCAL_RESIDUAL = ZERO_OBSERVED
G3_QHM2_ACTUAL_POLICY = NOT_RUN
G4_12_WORLD = ALIAS_BY_CONSTRUCTION
G6_G7_7_OF_7 = PERFECT_ORACLE_WIRING_ONLY
G7_T6 = UNKNOWN_NOT_RUN
FULL_EPISODE_COMPOSITION = NOT_MEASURED
NOVEL_MECHANISM_NECESSITY = NOT_SUPPORTED
NEXT_BOTTLENECK = OWNER_TRUTH_PRODUCTION_AND_CROSS_COMPONENT_CONFORMANCE
```

本综合未修改 `research/NOW.md`、`PROGRAM.md` 或任何正式研究状态。
