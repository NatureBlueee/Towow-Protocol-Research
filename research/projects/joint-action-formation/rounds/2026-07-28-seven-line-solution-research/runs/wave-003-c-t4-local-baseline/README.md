# T4 local method-neutral baseline

状态：`INDEPENDENT_EVALUATION_COMPLETE / PARTIAL`  
日期：2026-07-28

该候选是本地确定性 Authority/workflow 基线，不是新协议机制。它只读取 T4 solver allowlist，
并通过公开 controller 接口请求最小披露；没有读取 `oracle/truth.json`、migration truth 或
negative mutations。

## 方法

1. 从 blind input 枚举公开 Authority/request 接口；
2. 第一轮请求当前 tender、价格/容量/风险/stance、probe 条件、reservation 条件与目标域
   readback；
3. controller 对 probe、FIELD reservation 和 ASSURE reservation 返回 `DEFER`；
4. 在其前置披露完成后第二轮只重试三个 deferred request；
5. 取得 exact synthetic interop probe witness 与三个 version-bound reservation；
6. 构造 `CANDIDATE_NOT_COMMITMENT`，明确 final signatures、真实 submission、Adoption、
   Acceptance、Effect 和 Settlement 均未发生。

当前 controller 交互为 2 轮、31 个 receipts，其中包含第一轮 3 个 `DEFER` 及第二轮对应的
3 个成功结果。总价为 335000 CNY，低于 360000 CNY 上限。

## 冻结候选

- `output-v3/final-submission.json`
- SHA-256:
  `b7b9fc972b3c051841a37cc3af6a80f80459e0faf7458c57bffdb63737f2fd5a`
- schema validation: `PASS`
- independent semantic evaluation: `0.60 / PARTIAL`

独立 evaluator 对 R6 给出 `PASS`，对 R2/R3/R4/R5/R7 给出 `PARTIAL`。没有外部 outcome
false closure，也没有 critical `FAIL`；但候选把
`ALL_DISCLOSED_CONDITIONS_SATISFIED` 写得过强，当前 receipts 并没有证明 FIELD 风险已经被
Authority 分配，也没有证明 ASSURE audit scope 已在 implementation freeze 前冻结。

静态 mutation 结果为 `3 PASS / 4 PARTIAL / 3 UNKNOWN`，未达到 critical mutation closure；
migration 为 `UNKNOWN / NOT_RUN`。完整结果在
`output-v3/independent-evaluation.json`。这次评价是同模型不同上下文，不构成模型多样性。

`output/` 是第一版客户端误把 `results` 当作 `receipts` 的失败运行；`output-v2/` 是第二版
客户端误把 `history_hash` 当作 `previous_round_hash` 的失败运行。它们都不是候选结果。
`output-v3/` 才是当前冻结运行。

## 证据边界

这是高保真合成任务中的本地方法基线。controller response、probe 和 reservation 都是合成
truth，不是现实投标、真实主体 stance、资源占用或城市效果。当前候选代码仍针对 T4 接口
构造，migration 只是计划；只有独立 mutation/migration evaluator 才能判断其是否硬编码。
