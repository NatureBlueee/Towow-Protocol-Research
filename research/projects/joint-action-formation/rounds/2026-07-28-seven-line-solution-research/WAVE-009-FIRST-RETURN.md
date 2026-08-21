# Wave 009 — 七线第一返回与下一实现选择

日期：2026-07-29  
状态：`FIRST RETURN INTEGRATED / TWO IMPLEMENTATIONS SELECTED`

## 第一层结果

四个认知单元已经分别重建七条线的问题、最强成熟组合、paired worlds、evaluator、反例和
下一实现。本轮没有发现“缺一项黑技术”可以解释完整问题，也没有发现成熟技术天然失败。

更准确的判断是：

> 成熟组件已经能覆盖大量有界子问题；它们尚未自动解决完整问题，主要因为完整任务的
> query genesis、Principal policy、RelationVersion、Authority、资源、target truth、
> dependency 和成本没有由同一实验冻结，也不能由同一个中心合法拥有。把这些成熟组件按
> 正确 truth owner 串联并闭合，若能通过留出 world，就是通爻的完整正向方案。

这不是“现有技术增量为零”的叙事。解题结果本身就是成果；只有真实残余才进入新机制研究。

## 七线保留的原生 truth

| 线 | 独立 truth | 不得由什么替代 |
|---|---|---|
| G1 | 在 actual policy/budget 下可发现并可形成 qualified handoff 的机会 | latent oracle、搜索结果、单边声明 |
| G2 | 共同关系的 stage、horizon、version、materiality 与 contribution | workflow green、policy Allow |
| G3 | 在冻结 action/response/privacy 边界下的 exists/actual/robust reachability | hindsight path、万能 human |
| G4 | attempt 前 exact operation 的 reliance prediction | 事后成功、同源 receipt 数量 |
| G5 | Principal-owned Mandate、Commitment、Reservation、revoke 与 Standing | controller account、role label |
| G6 | target domain 的 Effect、Adoption、Acceptance、Settlement | workflow 自报 completed |
| G7 | dependency-aware continue/recover/reopen 与 reuse surplus | 全停、全重开、telemetry 绿色 |

跨线只允许显式引用带版本的公开结果，不允许用一条线的 PASS 创建另一条线的事实。

## 四个单元的关键区分

### A — G1

主 recall 分母从“全部 latent opportunity”改为在 actual Principal policy、合法 observation
actions、预算与 horizon 下存在 evidence path 的 \(D_t^{actual}\)。零披露不可区分 world
不再被错误记为搜索漏检。ARD、catalog、local projection、privacy provider、reciprocal
probe 与强中心组合成为公平正基线。

详见 [WAVE-009-G1-DESIGN.md](./WAVE-009-G1-DESIGN.md)。

### B — G2 + G5

Relation 与 Authority 被正式拆成 crossed square：durable relation 可与当前 DENY 共存；
没有 durable relation 也可拥有合法 one-shot PERMIT。CMMN/BPMN、CLM、OpenFGA/Cedar/OPA、
scoped delegation、Commitment/Reservation ledger、强中心+HITL 的成熟组合必须先运行。

详见 [WAVE-009-G2-G5-DESIGN.md](./WAVE-009-G2-G5-DESIGN.md)。

### C — G3

QHM-2 将单一 reachable 拆成 `R_exists / R_actual / R_effect_robust / R_safe_robust /
R_terminal_robust`。合法拒绝可以使 effect robust 为假而 safe robust 为真；privacy
bootstrap 必须绑定 Principal、recipient、purpose、projection、retention 和 onward use。

详见 [WAVE-009-G3-DESIGN.md](./WAVE-009-G3-DESIGN.md)。

### D — G4 + G6 + G7

执行前预测、目标域 Effect ladder 与 dependency reopen 分由三个 evaluator。最强反例是未
表达依赖：两个决策前 transcript 完全相同，任何中心或协议都不能同时避免 unsafe rely 与
missed reuse。当前只具备 T6 mutation replay spec，尚无合格 base-run，不能报告覆盖。

详见 [WAVE-009-G4-G6-G7-DESIGN.md](./WAVE-009-G4-G6-G7-DESIGN.md)。

## 为什么已有技术没有自动解决我们的问题

第一返回把原因从泛泛的“集成不足”缩到八个可实验条件：

1. 搜索和目录只处理已表达对象；query/predicate 可能尚未形成；
2. 局部组件的输入合同不同，不能把 catalog、privacy match、policy Allow 和 workflow
   complete 当成同一种证据；
3. Principal 的披露、立场、授权、承诺、接受和撤销分属不同 Authority locus；
4. 动态 world 中 index、permission、reservation、model、goal 和 dependency 会独立漂移；
5. relation semantics 在 CMMN/CLM→BPMN/policy/summary 编译时可能丢失；
6. outbox/workflow/event log 不自动拥有外部 target truth，也不自动区分 Effect ladder；
7. 未表达依赖在 observation 上不可区分，强中心没有额外合法信息时同样无解；
8. 组合的披露、probe、验证、等待、人工、恢复和治理成本可能吞噬复用收益。

每一项都允许成熟组合完整解决；实验要测的是它在相同信息、Authority、预算和 truth owner
条件下是否真的解决，而不是预设需要新协议。

## 下一实现选择

选择标准：

- 会不会改变多条后续结论；
- 是否修复当前最弱但最承重的证据；
- 能否区分成熟组合完整覆盖与精确残余；
- 是否已有可执行 truth/evaluator，而不是依赖尚不存在的 base-run；
- 是否避免继续只研究 G3。

| 候选 | 信息增益 | 当前可执行性 | 与最近工作的分布差异 | 决定 |
|---|---:|---:|---:|---|
| G1 `QUERY-GENESIS-DISCOVERY` | 很高 | 高 | 很高 | **立即实现** |
| G2+G5 `RELATION/AUTHORITY CROSSED SQUARE` | 很高 | 高 | 很高 | **立即实现** |
| G3 QHM-2 | 高 | 高 | 中；Wave 008 已集中推进 G3 | 设计冻结，下一波实现 |
| G4+G6+G7 T6 replay | 很高 | 低；缺合格 base-run/oracle graph | 高 | 先创建前置条件，不伪造运行 |

因此下一步启动两个实现：

1. `T1-HW-C / QUERY-GENESIS-DISCOVERY`；
2. `T3/T4 RELATION-AUTHORITY CROSSED-SQUARE`。

实现者不得是对应设计者。实现结束后再由另外的 Agent 做 mutation attack；同一实现者不得
通过修改 truth 或 evaluator 使自己的策略重新通过。

## 暂缓不等于否定

- QHM-2 的设计已冻结，暂缓是为了避免 G3 持续占用全部研究注意力，不是低估 Principal
  policy、robust refusal 或 privacy bootstrap；
- T6 设计价值很高，但必须先有合格 synthetic base trace 与独立 oracle dependency graph；
  在此之前报告覆盖率会重犯“规格绿灯冒充现实闭环”的历史错误；
- 两个立即实现的实验都必须让强中心、成熟组合和平台 direct 充分发挥。若它们完整解决，
  该结果将被登记为本轮最重要的正向成果之一。

本文件不修改正式 Problem、NAC 或任何 MechanismProfile 状态。
