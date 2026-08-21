# Wave 009 Unit A — G1 discovery before search

日期：2026-07-29  
状态：`INDEPENDENT DESIGN COMPLETE / NOT RUN`

## 这条线真正要评价什么

G1 不能再用“全部 latent opportunity recall”作为主分母。必须冻结三层不同的 truth：

\[
L_t \supseteq D_t^{actual} \supseteq H_t
\]

- \(L_t\)：oracle 知道的潜在互补关系；不表示它可观察、愿意披露或已经资格化。
- \(D_t^{actual}\)：在实际 Principal policy、允许的 observation/projection/probe action、
  预算 \(B\) 和 horizon \(H\) 下，存在合法 evidence path 的机会。
- \(H_t\)：已经获得当前、双向、authority-valid evidence，足以交给 G2 的
  `CANDIDATE_NOT_COMMITMENT`。

主 recall 只对 \(D_t^{actual}\) 计算；\(L_t-D_t^{actual}\) 必须单列为 policy-unfindable、
information-theoretically indistinguishable、refused 或 Unknown。否则系统会把“主体合法
选择零披露”错误写成算法漏检，并在理论上奖励越权。

## 冻结变量

| 变量 | 值域或作用 |
|---|---|
| `goal_state` | `VAGUE_SEED / TASK_PROJECTION / EXPLICIT_QUERY`；query genesis 必须有 provenance |
| `expression_state_i` | `UNEXPRESSED / PROJECTED / INDEXED`，绑定主体、方向、任务和版本 |
| `direction_i` | `SEEK / OFFER / AMBIGUOUS`；facet 相似不能推出方向互补 |
| `index_state` | snapshot、canonical head、entry version、有效期和 update lag |
| `local_trigger_state` | 未触发、触发、被 policy 阻止；记录来源和检测时延 |
| `predicate_state` | `SHARED_EXECUTABLE / LOCAL_ONLY / NOT_YET_FORMED` |
| `disclosure_policy` | recipient、purpose、retention、depth、onward、budget、revocation |
| `response_state` | `PROJECTION / WITNESS / CUT / UNKNOWN / UNWILLING_TO_DISCLOSE / NEGATIVE_ATTESTATION` |
| `population_scope` | `OPEN / CLOSED_VERSIONED`；只有后者可能支持 bounded `ABSENT` |
| `probe_state` | 双方 proposal、response、receipt、version、terminal |
| `freshness_state` | current head、receipt age、revocation epoch、invalidation delivery |
| `observability_class` | index/local trigger/probe discoverable、policy unfindable、信息不可区分 |
| `handoff_state` | `NONE / CANDIDATE_NOT_COMMITMENT`，绑定同一 detection/evidence closure |
| `resource_account` | 扫描、模型、索引、endpoint、probe、人类、时延和披露 exposure |

四种容易混淆的状态必须按证据而不是名称判断：

- `UNEXPRESSED`：local truth 存在，尚未索引，但存在 policy 允许的 projection path；
- `UNKNOWN`：开放世界内没有足够当前证据，例如 offline、timeout 或模型未覆盖；
- `UNWILLING_TO_DISCLOSE`：Authority 对精确 recipient/purpose/depth 给出可验证拒绝；
- `ABSENT`：冻结的 closed population 中，全部 eligible member 对同一版本 claim 给出当前
  负证据，只能是 scope-bound absence。

## 当前最强现成组合

```text
local event/value trigger
→ policy-bound task projection + query genesis
→ current-head validated ARD/catalog or strong-center routing
→ shared-predicate privacy match（条件成立时）
→ receipt-backed reciprocal probe/local oracle
→ versioned CANDIDATE_NOT_COMMITMENT handoff to G2
```

路由优先级：

1. T5 固定平台、精确 query、current canonical object：平台或白名单 adapter 直接完成；
2. 已表达且 current：ARD/catalog 索引与路由；
3. 未表达但 local trigger 可观察：端侧模型或规则生成最小 projection；
4. 已有 shared executable predicate 但不宜披露原值：PSI/MPC/TEE 类 provider 只给限定
   compatibility witness，并报告 leakage 和 trust；
5. coarse candidate 仍不足：双方 local oracle 运行 purpose-bound reciprocal probe；
6. 拒绝、offline、零披露或 predicate 未形成：返回 typed boundary，不制造候选。

强中心是完整正基线：它可以集中规划、生成 query、选择 probe、组合目录和隐私 provider，
但只能读取其他方法也能合法取得的 observation，不能替 Principal 披露、拒绝或认领 handoff。
在允许合法集中披露的 world 中，它应获得 raw input 并支付 exposure cost；完整解决即为通爻
正向方案。

## 现成组合完整解决的条件与精确残余

完整解决要求：

- 至少一个权威端能从模糊目标产生相关 local trigger；
- 必要事实能被投影成可验证 projection 或 shared predicate；
- 存在至少一条 policy-compliant communication path；
- current head/revocation 可读；
- Principal actual policy 在 horizon 内响应；
- reciprocal evidence 足够支撑当前 handoff。

仍未解决的不是“检索更弱”，而是以下精确条件：

1. 两 world 的全部合法 transcript 相同，任何系统都无法区分；
2. 新机会依赖当前 vocabulary 和目标都没有表达的维度，query/predicate 不可生成；
3. open population 中沉默、未扫描、offline 与不存在不可区分；
4. 主体拒绝披露时，正确结果是边界或停止；
5. G1 的 freshness 只到 handoff 时刻，后续撤销由 G2/G7 重新校验；
6. 签名 projection 不证明 capability、resource、authorization 或 Effect；
7. compatibility predicate 本身若需互动形成，G1 只能给出 proposal；
8. 对每个模糊目标广播并调用所有 endpoint 高级模型会违反 V2 的成本和边界；
9. provenance 不证明陈述诚实，也不解决 Sybil 和激励。

隐私计算只能减少“已有共享谓词”上的泄露，不能凭空形成 query、feature 或关系语义。

## Paired worlds

| Pair | 唯一冻结差异 | 正确区分 |
|---|---|---|
| `E-INDEXED / E-UNEXPRESSED` | 相同 latent complement；current indexed projection vs local-only fact | catalog 只成功前者；local-trigger 组合恢复后者 |
| `U-COMPAT / U-DIRECTION-DECOY` | coarse facet 相同；SEEK/OFFER vs SEEK/SEEK | 只有前者 handoff |
| `S-ACTIVE / S-REVOKED` | public cache 同为 v1；canonical head ACTIVE v1 vs REVOKED v2 | 必须 current-head readback |
| `N-NEW-FACT / N-NO-FACT` | index 都无条目；端侧 event 有互补 fact vs 无 fact | local trigger 区分；catalog 保守相同 |
| `Q-*` 四态 | projection path、offline、signed refusal、closed-negative closure | 分别输出 UNEXPRESSED/UNKNOWN/UNWILLING/ABSENT |
| `Z-EXISTS / Z-ABSENT` | latent complement 存在 vs 不存在；所有合法 transcript 相同 | 输出必须相同；存在 world 不计 recall miss |
| `R-MUTUAL / R-ONE-SIDED` | 双方 probe success vs 一方拒绝/timeout | 只有前者 handoff |
| `P-SHARED / P-NO-PREDICATE` | 有 shared executable predicate vs 没有 | privacy provider 只在前者可判 |
| `C-RAW-ALLOWED / C-RAW-FORBIDDEN` | Authority 是否允许中心读取 raw | 前者中心可完整解决；后者 local oracle 或停止 |
| `T5-DIRECT / T5-NO-MATCH` | current SKU 存在 vs 平台 Authority 返回 no-match | 平台直达或权威 no-match，不启动跨主体 probe |

## Evaluator

每个 world 冻结 \(L_t\)、local facts、index snapshots、canonical heads、actual Principal
policies、allowed action/observation graph、预算，以及由 runner 在有限模型中计算的
\(D_t^{actual}\) 与 G2 handoff qualification predicate。

分别报告：

- `actual-policy recall`：对 \(D_t^{actual}\)；
- `robust safety`：所有允许 refusal/stale/timeout 分支无越权披露、false absence、false handoff；
- `existential discoverability`：只作为 world capability；
- 合法拒绝导致 robust liveness false，不记方法失败。

硬失败包括：

- unauthorized disclosure；
- open-world false `ABSENT`；
- stale/revoked、SEEK/SEEK、不兼容或单边 probe handoff；
- handoff 偷渡 Commitment/Authority/Capability；
- oracle-derived query 注入 pre-query arm；
- candidate 自报 identity、truth、cost 或 receipt root；
- 零披露不可区分 pair 输出不同。

核心指标为 discoverable recall、handoff precision、false wakeup、四态 confusion、freshness、
refusal fidelity、query genesis provenance 和 T5 bypass overhead。披露不能压成一个字节数，
必须报告 origin facts、recipient、sensitivity、retention、onward hops、depth、cryptographic
leakage 与 policy violation 的向量，并给出 recall–exposure–latency Pareto frontier。

## 最强反例

在 `Z-EXISTS` 与 `Z-ABSENT` 中，双方 policy 禁止 projection、probe 和 derived disclosure，
公共事件、catalog、timeout、signed policy response 与全部允许 transcript 完全相同。

任何算法若输出不同，必然读取 truth 泄漏；若输出相同，就不可能同时发现存在 world 并准确
否定 absence。因此“零披露、完整 latent recall、无 false positive”三者原则上不可兼得。

对照正例同样重要：若全部 local facts 可合法集中、规模在预算内、current head 可读且
Principal policy 固定，强中心模型加平台 workflow 可以完整生成 query、发现组合、请求
Authority 并形成 G2 handoff；该 world 不需要新的端侧协议或 NAC。

## 下一实现

实现新的 `T1-HW-C / QUERY-GENESIS-DISCOVERY`，不修改历史 HW-A/HW-B：

1. 冻结上述 10 组 paired worlds、\(L/D/H\)、actual policies、budgets 和 evaluator；
2. 统一 runner API：
   `observe_goal_seed / poll_local_trigger / emit_projection / search_index /
   read_current_head / private_match / request_probe / handoff / stop`；
3. 实现 expressed-index/ARD、local projection、strong center + authoritative local oracle、
   privacy predicate provider、reciprocal probe、Router composition 六臂和 T5 direct 负控；
4. runner 持有 truth、identity、keys、raw operations、index head 与 evidence anchor；
5. world classification、qualified handoff、actual-policy recall、robust safety、cost/disclosure
   和 T5 bypass 分表；
6. release gate 是不可区分 pair 等价、stale 不误唤醒、四态不混、单边不 handoff、
   T5 零额外披露/probe、candidate 不能控制 truth/log/identity。

本设计没有运行 ARD、强中心、privacy provider 或组合；所有覆盖判断仍是 `NOT_RUN`。
